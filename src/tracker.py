import threading
import time
import os
import math
import ctypes
from ctypes import wintypes
import win32gui
import win32process
import win32api
import win32con
import psutil
from .database import Database
from .screen_time import split_interval_by_local_hour
import datetime
from collections import defaultdict

# Ctypes definitions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207
WM_MOUSEWHEEL = 0x020A

# CRITICAL: On 64-bit Windows, LPARAM and LRESULT are 64-bit
LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
LPARAM = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

# CRITICAL: Use proper types for 64-bit Windows
# HOOKPROC signature: LRESULT CALLBACK HookProc(int nCode, WPARAM wParam, LPARAM lParam)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, LPARAM)

# Set proper argument and return types for CallNextHookEx
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT

class ActivityTrack:
    def __init__(self, db_path="tracker.db"):
        self.db = Database(db_path)
        self.running = False
        
        # Buffers - use thread-safe access
        self.key_buffer = 0
        self.click_buffer = 0
        self.distance_buffer = 0.0  # Now in meters
        self.scroll_buffer = 0.0
        self.scroll_buffer = 0.0
        self.app_stats_buffer = {}  # {app_name: {'keys': 0, 'clicks': 0, 'scrolls': 0, 'distance': 0.0}}
        self.heatmap_buffer = {}
        self.mouse_heatmap_buffer = {}
        self.app_heatmap_buffer = {}  # {app_name: {key_code: count}}
        self.app_mouse_heatmap_buffer = {}  # {app_name: {(x, y): count}}
        
        # Screen time tracking
        # Buffer by (date, hour, app_name) to avoid dumping long spans into a single hour.
        # Values are float seconds.
        self.foreground_time_buffer = {}  # {(date, hour, app_name): seconds}
        self.current_foreground_app = None
        self.foreground_app_start_time = None
        
        # Idle detection
        self.last_activity_time = time.time()  # Last user input activity
        self.idle_timeout = 300  # Default 5 minutes (300 seconds)
        self.is_idle = False  # Current idle state
        self.idle_start_time = None  # When idle period started

        # Detect large wall-clock jumps (e.g. PC sleep/hibernate) so we don't
        # incorrectly count suspended time as foreground/idle usage.
        # Tracker loops run every 1s/5s, so anything much larger than that is
        # almost certainly suspend/resume.
        self.suspend_gap_threshold_seconds = 120.0
        self._last_wall_time_observed = None  # type: float | None
        
        self.lock = threading.Lock()
        self.last_mouse_pos = None
        self.cached_app_name = "Unknown"
        self.last_app_check = 0
        
        self.hook_thread = None
        self.hook_thread_id = None
        self.keyboard_hook = None
        self.mouse_hook = None
        
        # Track held keys to prevent counting repeats
        self.keys_held = set()
        
        # Screen metrics for distance calculation
        self._init_screen_metrics()

    def _add_foreground_duration(self, app_name: str, start_ts: float | None, end_ts: float | None) -> None:
        """Accumulate a duration into the foreground buffer, split by local hour/date."""
        if not app_name or app_name == "Unknown" or start_ts is None or end_ts is None:
            return
        if end_ts <= start_ts:
            return

        for date_part, hour_part, seconds in split_interval_by_local_hour(start_ts, end_ts):
            if seconds <= 0:
                continue
            key = (date_part, hour_part, app_name)
            self.foreground_time_buffer[key] = self.foreground_time_buffer.get(key, 0.0) + float(seconds)

    def _detect_and_handle_suspend_gap_unlocked(self, current_time: float) -> bool:
        """Detect a large wall-clock gap and reset tracking to avoid overcounting.

        Returns:
            True if a suspend-like gap was detected and tracking state was reset.
        """
        last = self._last_wall_time_observed
        self._last_wall_time_observed = float(current_time)
        if last is None:
            return False

        gap = float(current_time) - float(last)
        if gap <= float(self.suspend_gap_threshold_seconds):
            return False

        # Treat as a session break: do NOT attribute the gap to any app or idle.
        self.last_activity_time = float(current_time)
        self.is_idle = False
        self.idle_start_time = None
        if self.current_foreground_app is not None:
            self.foreground_app_start_time = float(current_time)
        return True

    def set_idle_timeout(self, seconds):
        """Set the idle timeout threshold in seconds.
        
        Args:
            seconds: Number of seconds of inactivity before considering user idle.
                    Set to 0 or negative to disable idle detection.
        """
        with self.lock:
            self.idle_timeout = max(0, seconds)
    
    def _update_activity_time(self):
        """Update last activity time. Called on any user input."""
        current_time = time.time()
        with self.lock:
            self.last_activity_time = current_time
            
            # If we were idle and now active, record the idle time
            if self.is_idle and self.idle_start_time:
                self._add_foreground_duration('[Idle]', self.idle_start_time, current_time)
                self.is_idle = False
                self.idle_start_time = None
                # Reset foreground tracking to current app
                self.foreground_app_start_time = current_time
    
    def _check_idle_state(self):
        """Check if user is idle based on last activity time.
        
        Returns:
            bool: True if user is currently idle
        """
        if self.idle_timeout <= 0:
            return False  # Idle detection disabled
        
        current_time = time.time()
        time_since_activity = current_time - self.last_activity_time
        return time_since_activity >= self.idle_timeout
    
    def _init_screen_metrics(self):
        """Initialize screen physical dimensions for accurate distance calculation.
        
        Uses Windows GDI to get physical screen size in millimeters.
        Falls back to estimation based on common 96 DPI if unavailable.
        """
        try:
            # Get device context for the screen
            hdc = user32.GetDC(None)
            
            # Get physical screen dimensions in millimeters
            # HORZSIZE (4) = Width in millimeters
            # VERTSIZE (6) = Height in millimeters
            self.screen_width_mm = gdi32.GetDeviceCaps(hdc, 4)  # HORZSIZE
            self.screen_height_mm = gdi32.GetDeviceCaps(hdc, 6)  # VERTSIZE
            
            # Get screen resolution in pixels
            # HORZRES (8) = Width in pixels  
            # VERTRES (10) = Height in pixels
            self.screen_width_px = gdi32.GetDeviceCaps(hdc, 8)   # HORZRES
            self.screen_height_px = gdi32.GetDeviceCaps(hdc, 10)  # VERTRES
            
            user32.ReleaseDC(None, hdc)
            
            # Calculate pixels per millimeter
            if self.screen_width_mm > 0 and self.screen_width_px > 0:
                self.px_per_mm = self.screen_width_px / self.screen_width_mm
            else:
                # Fallback: assume 96 DPI (common default)
                # 96 DPI = 96 pixels per inch = 96 / 25.4 pixels per mm
                self.px_per_mm = 96 / 25.4
                
        except Exception as e:
            print(f"Warning: Could not get screen metrics: {e}")
            # Fallback values
            self.screen_width_mm = 344  # ~13.5 inch laptop
            self.screen_height_mm = 194
            self.screen_width_px = 1920
            self.screen_height_px = 1080
            self.px_per_mm = 1920 / 344

    def start(self):
        self.running = True
        self.hook_thread = threading.Thread(target=self.hook_loop, daemon=True)
        self.hook_thread.start()
        
        # Start flush timer
        self.flush_thread = threading.Thread(target=self.flush_loop, daemon=True)
        self.flush_thread.start()
        
        # Start foreground window tracker
        self.foreground_thread = threading.Thread(target=self.foreground_track_loop, daemon=True)
        self.foreground_thread.start()

    def stop(self):
        self.running = False
        if self.hook_thread_id:
            user32.PostThreadMessageW(self.hook_thread_id, 0x0012, 0, 0)  # WM_QUIT
        # Flush remaining foreground time
        self._record_foreground_time()
        self.flush_stats()

    def foreground_track_loop(self):
        """Track foreground window changes every second."""
        while self.running:
            try:
                self._check_foreground_window()
            except Exception as e:
                pass  # Silently ignore errors
            time.sleep(1)

    def _check_foreground_window(self):
        """Check if foreground window has changed and record time.
        
        Also handles idle detection - if user is idle, time is recorded as '[Idle]'
        instead of the foreground application.
        """
        current_app = self.get_active_app_name()
        current_time = time.time()
        
        with self.lock:
            # If the process was suspended (sleep/hibernate), avoid counting the gap.
            if self._detect_and_handle_suspend_gap_unlocked(current_time):
                self.current_foreground_app = current_app
                self.foreground_app_start_time = current_time

            # Check if user has become idle
            was_idle = self.is_idle
            now_idle = self._check_idle_state_unlocked()
            
            if self.current_foreground_app is None:
                # First time initialization
                self.current_foreground_app = current_app
                self.foreground_app_start_time = current_time
                self.is_idle = now_idle
                if now_idle:
                    self.idle_start_time = current_time
            elif now_idle and not was_idle:
                # User just became idle - record time for current app up to this point
                if self.foreground_app_start_time:
                    # Time before idle should go to the app
                    # Use last_activity_time as the cutoff
                    active_duration = self.last_activity_time - self.foreground_app_start_time
                    if active_duration > 0 and self.current_foreground_app != "Unknown":
                        self._add_foreground_duration(self.current_foreground_app, self.foreground_app_start_time, self.last_activity_time)
                
                # Start tracking idle time
                self.is_idle = True
                self.idle_start_time = self.last_activity_time
                self.foreground_app_start_time = None  # Pause app tracking
                
            elif not now_idle and was_idle:
                # User returned from idle - this is handled in _update_activity_time
                # But just in case, ensure state is consistent
                self.is_idle = False
                if self.idle_start_time:
                    self._add_foreground_duration('[Idle]', self.idle_start_time, current_time)
                self.idle_start_time = None
                self.current_foreground_app = current_app
                self.foreground_app_start_time = current_time
                
            elif not now_idle and current_app != self.current_foreground_app:
                # Window changed while not idle, record time for previous app
                if self.foreground_app_start_time:
                    elapsed = current_time - self.foreground_app_start_time
                    if elapsed > 0 and self.current_foreground_app != "Unknown":
                        self._add_foreground_duration(self.current_foreground_app, self.foreground_app_start_time, current_time)
                
                # Start tracking new app
                self.current_foreground_app = current_app
                self.foreground_app_start_time = current_time
            
            # If idle, we don't update current_foreground_app - idle time is tracked separately
    
    def _check_idle_state_unlocked(self):
        """Check idle state without acquiring lock (for use when lock is already held)."""
        if self.idle_timeout <= 0:
            return False
        current_time = time.time()
        time_since_activity = current_time - self.last_activity_time
        return time_since_activity >= self.idle_timeout

    def _record_foreground_time(self):
        """Record current foreground app's accumulated time before flush."""
        current_time = time.time()
        with self.lock:
            # If we resumed from suspend, skip attributing the gap.
            if self._detect_and_handle_suspend_gap_unlocked(current_time):
                return

            if self.is_idle and self.idle_start_time:
                # Record accumulated idle time
                self._add_foreground_duration('[Idle]', self.idle_start_time, current_time)
                # Reset idle start time but keep idle state
                self.idle_start_time = current_time
            elif self.current_foreground_app and self.foreground_app_start_time:
                elapsed = current_time - self.foreground_app_start_time
                if elapsed > 0 and self.current_foreground_app != "Unknown":
                    self._add_foreground_duration(self.current_foreground_app, self.foreground_app_start_time, current_time)
                # Reset start time but keep current app
                self.foreground_app_start_time = current_time

    def get_foreground_time_snapshot(self):
        """Get a thread-safe snapshot of current foreground time buffer."""
        with self.lock:
            today = datetime.date.today()
            totals = defaultdict(float)
            for (date_part, _hour_part, app_name), seconds in self.foreground_time_buffer.items():
                if date_part == today and seconds > 0:
                    totals[app_name] += float(seconds)

            current_time = time.time()

            # Prevent snapshot from showing huge overcount after suspend/resume.
            if self._detect_and_handle_suspend_gap_unlocked(current_time):
                return dict(totals)
            
            if self.is_idle and self.idle_start_time:
                # Currently idle - add accumulated idle time
                for date_part, _hour_part, seconds in split_interval_by_local_hour(self.idle_start_time, current_time):
                    if date_part == today and seconds > 0:
                        totals['[Idle]'] += float(seconds)
            elif self.current_foreground_app and self.foreground_app_start_time:
                elapsed = current_time - self.foreground_app_start_time
                if elapsed > 0 and self.current_foreground_app != "Unknown":
                    for date_part, _hour_part, seconds in split_interval_by_local_hour(self.foreground_app_start_time, current_time):
                        if date_part == today and seconds > 0:
                            totals[self.current_foreground_app] += float(seconds)

            return dict(totals)

    def get_stats_snapshot(self):
        """Get a thread-safe snapshot of current buffers + DB stats."""
        with self.lock:
            db_stats = self.db.get_today_stats()
            if db_stats:
                # db_stats: date, key_count, mouse_click_count, mouse_distance, scroll_distance
                keys = db_stats[1] + self.key_buffer
                clicks = db_stats[2] + self.click_buffer
                distance = db_stats[3] + self.distance_buffer
                scroll = db_stats[4] + self.scroll_buffer
            else:
                keys = self.key_buffer
                clicks = self.click_buffer
                distance = self.distance_buffer
                scroll = self.scroll_buffer
            
            # Merge DB heatmap with current buffer
            # First get today's data from DB
            db_heatmap = self.db.get_today_heatmap()
            
            # Then merge with current buffer (buffer contains increments not yet flushed)
            merged_heatmap = dict(db_heatmap)
            for key_code, count in self.heatmap_buffer.items():
                merged_heatmap[key_code] = merged_heatmap.get(key_code, 0) + count
            
            # Also capture raw buffer values for live updates
            buffer_keys = self.key_buffer
            buffer_clicks = self.click_buffer
            buffer_distance = self.distance_buffer
            buffer_scroll = self.scroll_buffer
            buffer_heatmap = dict(self.heatmap_buffer)
            
            # Copy app-specific heatmap buffers
            app_heatmap_buffer_copy = {app: dict(keys) for app, keys in self.app_heatmap_buffer.items()}
            app_mouse_heatmap_buffer_copy = {app: dict(pos) for app, pos in self.app_mouse_heatmap_buffer.items()}
            
        return {
            'keys': keys,
            'clicks': clicks,
            'distance': distance,
            'scroll': scroll,
            'heatmap': merged_heatmap,
            'mouse_heatmap': dict(self.mouse_heatmap_buffer),
            # Buffer-only values for live updates
            'buffer_keys': buffer_keys,
            'buffer_clicks': buffer_clicks,
            'buffer_distance': buffer_distance,
            'buffer_scroll': buffer_scroll,
            'buffer_heatmap': buffer_heatmap,
            # App-specific heatmap buffers
            'app_heatmap_buffer': app_heatmap_buffer_copy,
            'app_mouse_heatmap_buffer': app_mouse_heatmap_buffer_copy
        }

    def get_active_app_info(self):
        """Returns (app_name, exe_path, pid)."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            try:
                name = process.name()
            except Exception as e:
                try:
                    case_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker_error.log")
                    with open(case_path, "a") as f:
                        f.write(f"{datetime.datetime.now()} - Error in process.name(): {e}\n")
                except:
                    pass
                name = "Unknown"
                
            try:
                exe = process.exe()
            except (psutil.AccessDenied, Exception):
                exe = None
                
            return name, exe, pid
        except Exception as e:
            # Debug logging to file
            try:
                case_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker_error.log")
                with open(case_path, "a") as f:
                    import traceback
                    f.write(f"{datetime.datetime.now()} - Error in get_active_app_info: {e}\n")
                    f.write(traceback.format_exc())
                    f.write("\n")
            except:
                pass
            return "Unknown", None, None

    def get_file_description(self, path):
        """Extract FileDescription from PE file using win32api."""
        if not path or not os.path.exists(path):
            return None
        try:
            # Get language/codepage pairs
            lang_info = win32api.GetFileVersionInfo(path, '\\VarFileInfo\\Translation')
            if not lang_info:
                return None
            
            # Construct the query string for the first language/codepage
            lang, codepage = lang_info[0]
            # Format: \StringFileInfo\040904B0\FileDescription
            query = f'\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription'
            
            return win32api.GetFileVersionInfo(path, query)
        except Exception:
            return None

    def _check_update_metadata(self, app_name, exe_path):
        """Update DB with metadata if we haven't seen this app yet."""
        if app_name == "Unknown": return
        
        # Simple cache to avoid re-querying DB/File every frame
        if hasattr(self, 'metadata_cache') and app_name in self.metadata_cache:
            return

        if not hasattr(self, 'metadata_cache'):
            self.metadata_cache = set()

        friendly_name = self.get_file_description(exe_path)
        if not friendly_name:
            friendly_name = app_name # Fallback
            
        # Strip .exe if fallback
        if friendly_name == app_name and friendly_name.lower().endswith('.exe'):
            friendly_name = friendly_name[:-4]
            # Capitalize?
            friendly_name = friendly_name.capitalize()
            
        try:
            self.db.update_app_metadata(app_name, friendly_name, exe_path)
            self.metadata_cache.add(app_name)
        except Exception:
            pass

    def get_active_app_name(self):
        # Wraps the detailed version for backward compatibility if needed, 
        # but better to integrate the metadata check here or in OnMove.
        try:
            name, path, _ = self.get_active_app_info()
            
            # Trace logging
            try:
                if not hasattr(self, 'trace_cache'): self.trace_cache = set()
                if name not in self.trace_cache:
                    case_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_trace.txt")
                    with open(case_path, "a") as f:
                        f.write(f"{datetime.datetime.now()} - Detected: {name} (Path: {path})\n")
                    self.trace_cache.add(name)
            except:
                pass

            if name != "Unknown":
                self._check_update_metadata(name, path)
            return name
        except Exception:
            return "Unknown"

    def low_level_keyboard_proc(self, nCode, wParam, lParam):
        # CRITICAL: Always call CallNextHookEx first to prevent blocking input
        result = user32.CallNextHookEx(self.keyboard_hook, nCode, wParam, lParam)
        try:
            if nCode >= 0:
                kb_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb_struct.vkCode
                
                if wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN:
                    # Only count if this is the initial press (key not already held)
                    if vk not in self.keys_held:
                        self.keys_held.add(vk)
                        # Check if it's a physical key (not injected)
                        if not (kb_struct.flags & 0x10):  # LLKHF_INJECTED
                            self.on_press(vk, kb_struct.scanCode)
                elif wParam == WM_KEYUP or wParam == WM_SYSKEYUP:
                    # Remove from held keys on release
                    self.keys_held.discard(vk)
        except Exception:
            pass
        return result

    def low_level_mouse_proc(self, nCode, wParam, lParam):
        # CRITICAL: Always call CallNextHookEx first to prevent blocking input
        result = user32.CallNextHookEx(self.mouse_hook, nCode, wParam, lParam)
        try:
            if nCode >= 0:
                ms_struct = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if wParam == WM_MOUSEMOVE:
                    self.on_move(ms_struct.pt.x, ms_struct.pt.y)
                elif wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                    self.on_click(ms_struct.pt.x, ms_struct.pt.y)
                elif wParam == WM_MOUSEWHEEL:
                    # mouseData high word is delta
                    delta = ctypes.c_short((ms_struct.mouseData >> 16) & 0xFFFF).value
                    self.on_scroll(delta)
        except Exception:
            pass
        return result

    def hook_loop(self):
        self.hook_thread_id = kernel32.GetCurrentThreadId()
        
        # Keep references to callbacks to prevent GC
        self.kb_proc = HOOKPROC(self.low_level_keyboard_proc)
        self.ms_proc = HOOKPROC(self.low_level_mouse_proc)
        
        self.keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.kb_proc, None, 0)
        self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self.ms_proc, None, 0)
        
        if not self.keyboard_hook or not self.mouse_hook:
            print(f"Failed to set hooks: KB={self.keyboard_hook}, MS={self.mouse_hook}")
            return
        
        msg = wintypes.MSG()
        # Use GetMessage which blocks efficiently until a message arrives
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0012: # WM_QUIT
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        
        user32.UnhookWindowsHookEx(self.keyboard_hook)
        user32.UnhookWindowsHookEx(self.mouse_hook)

    def on_press(self, vk_code, scan_code):
        self._update_activity_time()  # Update last activity for idle detection
        with self.lock:
            self.key_buffer += 1
            
            # App stats
            app_name = self.get_active_app_name()
            if app_name not in self.app_stats_buffer:
                self.app_stats_buffer[app_name] = {'keys': 0, 'clicks': 0, 'scrolls': 0, 'distance': 0.0}
            self.app_stats_buffer[app_name]['keys'] += 1
            
            # Heatmap stats (global)
            self.heatmap_buffer[scan_code] = self.heatmap_buffer.get(scan_code, 0) + 1
            
            # App-specific heatmap
            if app_name not in self.app_heatmap_buffer:
                self.app_heatmap_buffer[app_name] = {}
            self.app_heatmap_buffer[app_name][scan_code] = self.app_heatmap_buffer[app_name].get(scan_code, 0) + 1

    def on_move(self, x, y):
        self._update_activity_time()  # Update last activity for idle detection
        if self.last_mouse_pos:
            # Calculate pixel distance
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            dist_px = math.sqrt(dx * dx + dy * dy)
            
            # Convert pixels to meters:
            # dist_px / px_per_mm = distance in mm
            # distance in mm / 1000 = distance in meters
            dist_meters = dist_px / self.px_per_mm / 1000.0
            
            with self.lock:
                self.distance_buffer += dist_meters
                
                # Update app distance (throttled check for active app)
                now = time.time()
                if now - self.last_app_check > 0.5: # Check active app every 500ms
                    self.cached_app_name = self.get_active_app_name()
                    self.last_app_check = now
                
                app = self.cached_app_name
                if app not in self.app_stats_buffer:
                    self.app_stats_buffer[app] = {'keys': 0, 'clicks': 0, 'scrolls': 0, 'distance': 0.0}
                self.app_stats_buffer[app]['distance'] += dist_meters
        self.last_mouse_pos = (x, y)

    def on_click(self, x=0, y=0):
        self._update_activity_time()  # Update last activity for idle detection
        with self.lock:
            self.click_buffer += 1
            
            # App stats
            app = self.get_active_app_name()
            if app not in self.app_stats_buffer:
                self.app_stats_buffer[app] = {'keys': 0, 'clicks': 0, 'scrolls': 0, 'distance': 0.0}
            self.app_stats_buffer[app]['clicks'] += 1
            
            # Track mouse heatmap (x, y) - global
            # Bin to 5x5 pixels
            bx = (x // 5) * 5
            by = (y // 5) * 5
            self.mouse_heatmap_buffer[(bx, by)] = self.mouse_heatmap_buffer.get((bx, by), 0) + 1
            
            # App-specific mouse heatmap
            if app not in self.app_mouse_heatmap_buffer:
                self.app_mouse_heatmap_buffer[app] = {}
            self.app_mouse_heatmap_buffer[app][(bx, by)] = self.app_mouse_heatmap_buffer[app].get((bx, by), 0) + 1

    def on_scroll(self, delta):
        self._update_activity_time()  # Update last activity for idle detection
        with self.lock:
            self.scroll_buffer += abs(delta) / 120.0
            
            # App stats
            app = self.get_active_app_name()
            if app not in self.app_stats_buffer:
                self.app_stats_buffer[app] = {'keys': 0, 'clicks': 0, 'scrolls': 0, 'distance': 0.0}
            self.app_stats_buffer[app]['scrolls'] += 1

    def flush_loop(self):
        while self.running:
            time.sleep(5)
            self._record_foreground_time()  # Record current foreground time before flush
            self.flush_stats()

    def flush_stats(self):
        with self.lock:
            has_input = (self.key_buffer > 0 or self.click_buffer > 0 or 
                         self.distance_buffer > 0 or self.scroll_buffer > 0)
            
            # Check if foreground time buffer has any non-zero values
            has_time = any(s > 0 for s in self.foreground_time_buffer.values())

            if not has_input and not has_time:
                return

            today = datetime.date.today()
            current_hour = datetime.datetime.now().hour
            
            if has_input:
                self.db.update_stats(
                    today, 
                    self.key_buffer, 
                    self.click_buffer, 
                    self.distance_buffer, 
                    self.scroll_buffer
                )
                
                for app, stats in self.app_stats_buffer.items():
                    self.db.update_app_stats(today, app, 
                        key_count=stats['keys'], 
                        click_count=stats['clicks'],
                        scroll_count=stats['scrolls'],
                        distance=stats['distance']
                    )
                    
                    # Granular hourly stats
                    self.db.update_hourly_app_stats(today, current_hour, app,
                        key_count=stats['keys'], 
                        clicks=stats['clicks'],
                        scrolls=stats['scrolls'],
                        distance=stats['distance']
                    )
                
                for key_code, count in self.heatmap_buffer.items():
                    self.db.update_heatmap(today, key_code, count)
                    
                for (x, y), count in self.mouse_heatmap_buffer.items():
                    self.db.update_mouse_heatmap(today, x, y, count)
                
                # Flush app-specific heatmap data
                for app_name, key_counts in self.app_heatmap_buffer.items():
                    for key_code, count in key_counts.items():
                        self.db.update_app_heatmap(today, app_name, key_code, count)
                
                for app_name, pos_counts in self.app_mouse_heatmap_buffer.items():
                    for (x, y), count in pos_counts.items():
                        self.db.update_app_mouse_heatmap(today, app_name, x, y, count)

                # Reset input buffers
                self.key_buffer = 0
                self.click_buffer = 0
                self.distance_buffer = 0.0
                self.scroll_buffer = 0.0
                self.app_stats_buffer.clear()
                self.heatmap_buffer.clear()
                self.mouse_heatmap_buffer.clear()
                self.app_heatmap_buffer.clear()
                self.app_mouse_heatmap_buffer.clear()
            
            if has_time:
                # Flush foreground time buffer
                for (date_part, hour_part, app_name), seconds in self.foreground_time_buffer.items():
                    if seconds > 0:
                        self.db.update_foreground_time(date_part, hour_part, app_name, int(seconds))
                
                self.foreground_time_buffer.clear()

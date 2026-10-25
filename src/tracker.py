"""Queue-based input recording with atomic persistence and non-overlapping time."""
import ctypes
from ctypes import wintypes
from collections import defaultdict
from dataclasses import dataclass
import datetime
import logging
import math
import os
import queue
import threading
import time

import psutil
import win32api
import win32gui
import win32process

from .database import Database
from .screen_time import split_interval_by_local_hour
from .native_input import (
    NativeInputCapture, user32, KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT,
    WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP,
    WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_MOUSEWHEEL,
)

logger = logging.getLogger(__name__)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int


@dataclass(frozen=True, slots=True)
class CapturedEvent:
    kind: str
    wall_time: float
    monotonic_time: float
    payload: tuple
    hwnd: int | None
    generation: int


class ActivityTrack:
    def __init__(self, db_path="tracker.db", *, queue_limit=65536):
        self.db = Database(db_path)
        self.lock = threading.RLock()
        self._lifecycle_lock = threading.Lock()
        self.running = False
        self._closed = False
        self.hourly_input_buffer = {}
        self.hourly_app_stats_buffer = {}
        self.heatmap_buffer = {}
        self.mouse_heatmap_buffer = {}
        self.app_heatmap_buffer = {}
        self.app_mouse_heatmap_buffer = {}
        self.foreground_time_buffer = {}
        self._metadata_pending = {}
        self.metadata_cache = {}
        self._app_info_cache = {}
        self.current_foreground_app = None
        self.foreground_app_start_time = None
        self.last_activity_time = time.time()
        self.idle_timeout = 300
        self.is_idle = False
        self.idle_start_time = None
        self.suspend_gap_threshold_seconds = 10.0
        self._last_wall_time_observed = None
        self._last_monotonic_time_observed = None
        self._paused_reasons = set()
        self.last_mouse_pos = None
        self._events = queue.SimpleQueue()
        self._queue_limit = max(1, int(queue_limit))
        self._generation = 0
        self._accepting_events = True
        self._stop_event = threading.Event()
        self._shutdown_time = None
        self._shutdown_error = None
        self._capture = NativeInputCapture(self._enqueue_event)
        self.keys_held = self._capture.keys_held
        self.worker_thread = None
        self.hook_thread = None
        self.flush_thread = None
        self.foreground_thread = None
        self._hooks_requested = False
        self._last_worker_tick = time.monotonic()
        self.last_flush_time = None
        self.write_error = None
        self.processing_error = None
        self.dropped_events = 0
        self.retention_days = -1
        self._last_retention_date = None
        self._init_screen_metrics()

    def _enqueue_event(self, kind, payload=(), hwnd=None):
        """Called by hooks: never acquire recorder/database locks or perform I/O."""
        if not self._accepting_events:
            return False
        # A SimpleQueue never waits for the consumer. Bound input backlog while
        # allowing rare session/stop controls to be delivered even at capacity.
        if kind != 'session' and self._events.qsize() >= self._queue_limit:
            self.dropped_events += 1
            return False
        event = CapturedEvent(kind, time.time(), time.monotonic(), payload, hwnd, self._generation)
        self._events.put(event)
        return True

    def _process_event(self, event):
        with self.lock:
            if event.generation != self._generation:
                return
            if event.kind == 'session':
                self._handle_session_state(*event.payload, now=event.wall_time, monotonic_time=event.monotonic_time)
                return
            if self._paused_reasons:
                return
            name = self.get_active_app_name(event.hwnd)
            handlers = {'key': self.on_press, 'move': self.on_move,
                        'click': self.on_click, 'scroll': self.on_scroll}
            handlers[event.kind](*event.payload, timestamp=event.wall_time,
                                 monotonic_time=event.monotonic_time, app_name=name)

    def start(self, *, install_hooks=True):
        with self._lifecycle_lock:
            if self.running:
                return
            if self._closed or self._shutdown_time is not None:
                raise RuntimeError('Create a new recorder after shutdown')
            self.running = True
            self._hooks_requested = install_hooks
            self._stop_event.clear()
            self.worker_thread = threading.Thread(target=self.flush_loop, name='ActivityTrack recorder', daemon=True)
            self.flush_thread = self.worker_thread
            self.worker_thread.start()
            if install_hooks:
                self._capture.start()
                self.hook_thread = self._capture.thread

    def stop(self):
        """Stop capture, drain queued events, save, then close. Safe to call twice."""
        with self._lifecycle_lock:
            if self._closed:
                return
            self._accepting_events = False
            if self._shutdown_time is None:
                self._shutdown_time = (time.time(), time.monotonic())
            self._capture.stop()
            self.running = False
            self._stop_event.set()
            self._events.put(None)
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(15)
                if self.worker_thread.is_alive():
                    raise RuntimeError('The recorder is still saving; please retry shutdown')
                if self._shutdown_error is not None:
                    raise RuntimeError('Could not save pending activity; please retry shutdown') from self._shutdown_error
            else:
                # Also supports retrying a failed final write and diagnostic mode.
                while not self._events.empty():
                    event = self._events.get_nowait()
                    if event is not None:
                        self._process_event(event)
                self._record_foreground_time(*self._shutdown_time)
                self.flush_stats()
                self._shutdown_error = None
            self.db.close()
            self._closed = True

    def flush_loop(self):
        next_poll = time.monotonic()
        next_flush = next_poll + 5.0
        processed = 0
        while not self._stop_event.is_set() or not self._events.empty():
            try:
                event = self._events.get(timeout=0.1)
                if event is not None:
                    self._process_event(event)
            except queue.Empty:
                pass
            except Exception as error:
                self.processing_error = str(error)
                logger.exception('Unable to process an activity event')
            self._last_worker_tick = time.monotonic()
            processed += 1
            if processed < 256 and not self._events.empty():
                continue
            processed = 0
            now = time.monotonic()
            if not self._stop_event.is_set() and self._events.empty() and now >= next_poll:
                try:
                    self._check_foreground_window()
                except Exception as error:
                    self.processing_error = str(error)
                    logger.exception('Unable to update foreground time')
                next_poll = time.monotonic() + 1.0
            if not self._stop_event.is_set() and now >= next_flush:
                try:
                    # Never advance time past input events waiting in the queue.
                    if self._events.empty():
                        self._record_foreground_time()
                    self.flush_stats()
                    self._apply_retention()
                except Exception as error:
                    self.write_error = str(error)
                    logger.exception('Unable to save activity; the batch remains buffered')
                next_flush = time.monotonic() + 5.0
        try:
            self._record_foreground_time(*(self._shutdown_time or (time.time(), time.monotonic())))
            self.flush_stats()
        except Exception as error:
            self._shutdown_error = error
            self.write_error = str(error)
            logger.exception('Unable to save the final activity batch')

    def get_health_snapshot(self):
        return {
            'running': self.running,
            'hooks_active': bool(self._capture.keyboard_hook and self._capture.mouse_hook),
            'hooks_requested': self._hooks_requested,
            'hook_error': self._capture.last_error,
            'write_error': self.write_error,
            'processing_error': self.processing_error,
            'dropped_events': self.dropped_events,
            'queue_depth': self._events.qsize(),
            'last_flush_time': self.last_flush_time,
            'worker_delayed': self.running and time.monotonic() - self._last_worker_tick > 10,
            'paused': bool(self._paused_reasons),
        }

    def notify_session_state(self, paused, reason):
        self._enqueue_event('session', (bool(paused), reason))

    def _handle_session_state(self, paused, reason, *, now=None, monotonic_time=None):
        now = time.time() if now is None else now
        with self.lock:
            if not self._paused_reasons:
                self._advance_time_unlocked(now, monotonic_time)
            if paused:
                self._paused_reasons.add(reason)
            else:
                self._paused_reasons.discard(reason)
            self._reset_time_unlocked(now)
            self._last_wall_time_observed = now
            self._last_monotonic_time_observed = monotonic_time
            if not self._paused_reasons:
                self.current_foreground_app = None
                self.foreground_app_start_time = None

    def _reset_time_unlocked(self, now):
        self.last_activity_time = now
        self.is_idle = False
        self.idle_start_time = None
        self.foreground_app_start_time = now if self.current_foreground_app else None
        self.last_mouse_pos = None
        self._capture.reset_held_keys()

    def _detect_and_handle_suspend_gap_unlocked(self, current_time, monotonic_time=None):
        last = self._last_wall_time_observed
        last_mono = self._last_monotonic_time_observed
        if monotonic_time is not None and last_mono is not None and monotonic_time < last_mono:
            return False  # A late queued event is not a system clock adjustment.
        self._last_wall_time_observed = current_time
        self._last_monotonic_time_observed = monotonic_time
        if last is None:
            return False
        gap = current_time - last
        clock_changed = (monotonic_time is not None and last_mono is not None
                         and abs(gap - (monotonic_time - last_mono)) > 5.0)
        if gap < 0 or gap > self.suspend_gap_threshold_seconds or clock_changed:
            self._reset_time_unlocked(current_time)
            return True
        return False

    def _add_foreground_duration(self, app_name, start_ts, end_ts):
        if not app_name or app_name == 'Unknown' or start_ts is None or end_ts is None:
            return
        for date, hour, seconds in split_interval_by_local_hour(start_ts, end_ts):
            key = (date, hour, app_name)
            self.foreground_time_buffer[key] = self.foreground_time_buffer.get(key, 0.0) + seconds

    def _time_intervals_unlocked(self, now):
        if self._paused_reasons or self.current_foreground_app is None:
            return []
        cursor = self.idle_start_time if self.is_idle else self.foreground_app_start_time
        if cursor is None or now <= cursor:
            return []
        # Time before the configured idle threshold is active; all later time is
        # idle. No interval is ever retroactively counted a second time.
        cutoff = self.last_activity_time + self.idle_timeout if self.idle_timeout > 0 else math.inf
        intervals = []
        active_end = min(now, cutoff)
        if active_end > cursor:
            intervals.append((self.current_foreground_app, cursor, active_end))
        idle_start = max(cursor, cutoff)
        if now > idle_start:
            intervals.append(('[Idle]', idle_start, now))
        return intervals

    def _advance_time_unlocked(self, now, monotonic_time=None):
        if self._detect_and_handle_suspend_gap_unlocked(now, monotonic_time):
            return
        if self._paused_reasons:
            return
        for app, start, end in self._time_intervals_unlocked(now):
            self._add_foreground_duration(app, start, end)
        cursor = self.idle_start_time if self.is_idle else self.foreground_app_start_time
        if cursor is not None and now < cursor:
            return
        self.is_idle = self._check_idle_state_unlocked(now)
        self.idle_start_time = now if self.is_idle else None
        self.foreground_app_start_time = None if self.is_idle else now

    def _update_activity_time(self, current_time=None, monotonic_time=None, app_name=None):
        now = time.time() if current_time is None else current_time
        mono = time.monotonic() if monotonic_time is None else monotonic_time
        with self.lock:
            self._advance_time_unlocked(now, mono)
            self.last_activity_time = max(self.last_activity_time, now)
            if app_name is not None:
                self.current_foreground_app = app_name
            self.is_idle = False
            self.idle_start_time = None
            self.foreground_app_start_time = max(now, self._last_wall_time_observed or now)

    def _check_idle_state_unlocked(self, now=None):
        now = time.time() if now is None else now
        return self.idle_timeout > 0 and now - self.last_activity_time >= self.idle_timeout

    def _check_idle_state(self):
        with self.lock:
            return self._check_idle_state_unlocked()

    def set_idle_timeout(self, seconds):
        with self.lock:
            self._advance_time_unlocked(time.time(), time.monotonic())
            self.idle_timeout = max(0, int(seconds))

    def _check_foreground_window(self):
        with self.lock:
            if self._paused_reasons:
                return
            name = self.get_active_app_name()
            now = time.time()
            self._advance_time_unlocked(now, time.monotonic())
            self.current_foreground_app = name

    def _record_foreground_time(self, timestamp=None, monotonic_time=None):
        now = time.time() if timestamp is None else timestamp
        mono = time.monotonic() if monotonic_time is None else monotonic_time
        with self.lock:
            self._advance_time_unlocked(now, mono)

    def get_foreground_time_snapshot(self):
        with self.lock:
            today = datetime.date.today()
            totals = defaultdict(float)
            for (date, hour, app), seconds in self.foreground_time_buffer.items():
                if date == today:
                    totals[app] += seconds
            now = time.time()
            last = self._last_wall_time_observed
            if last is not None and (now < last or now - last > self.suspend_gap_threshold_seconds):
                return dict(totals)
            for app, start, end in self._time_intervals_unlocked(now):
                if app != 'Unknown':
                    for date, hour, seconds in split_interval_by_local_hour(start, end):
                        if date == today:
                            totals[app] += seconds
            return dict(totals)

    def get_active_app_info(self, hwnd=None):
        try:
            hwnd = win32gui.GetForegroundWindow() if hwnd is None else hwnd
            if not hwnd:
                return 'Unknown', None, None
            now = time.monotonic()
            cached = self._app_info_cache.get(hwnd)
            if cached is not None and now < cached[0]:
                return cached[1]
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            name = process.name()
            try:
                path = process.exe()
            except (psutil.Error, OSError):
                path = None
            result = (name, path, pid)
            if len(self._app_info_cache) >= 256:
                self._app_info_cache.clear()
            self._app_info_cache[hwnd] = (now + 0.5, result)
            return result
        except (psutil.Error, OSError, RuntimeError):
            return 'Unknown', None, None
        except Exception:
            # Foreground windows can disappear between either Win32 query.
            return 'Unknown', None, None

    def _check_update_metadata(self, app_name, exe_path):
        if app_name == 'Unknown':
            return
        with self.lock:
            if app_name in self.metadata_cache and (not exe_path or self.metadata_cache[app_name] == exe_path):
                return
            friendly = self.get_file_description(exe_path) or app_name.removesuffix('.exe')
            self._metadata_pending[app_name] = (friendly, exe_path)
            self.metadata_cache[app_name] = exe_path

    def get_active_app_name(self, hwnd=None):
        name, path, _ = self.get_active_app_info(hwnd)
        self._check_update_metadata(name, path)
        return name

    def low_level_keyboard_proc(self, code, message, address):
        return self._capture.keyboard_proc(code, message, address)

    def low_level_mouse_proc(self, code, message, address):
        return self._capture.mouse_proc(code, message, address)

    def _input_context(self, timestamp, monotonic_time, app_name):
        now = time.time() if timestamp is None else timestamp
        name = self.get_active_app_name() if app_name is None else app_name
        self._update_activity_time(now, monotonic_time, name)
        moment = datetime.datetime.fromtimestamp(now)
        return (moment.date(), moment.hour), name

    @staticmethod
    def _empty_input():
        return {'keys': 0, 'clicks': 0, 'distance': 0.0, 'scroll': 0.0}

    @staticmethod
    def _empty_app():
        return {'keys': 0, 'clicks': 0, 'distance': 0.0, 'scrolls': 0.0}

    def on_press(self, vk_code, scan_code, *, timestamp=None, monotonic_time=None, app_name=None):
        with self.lock:
            if self._paused_reasons:
                return
            (date, hour), app = self._input_context(timestamp, monotonic_time, app_name)
            self.hourly_input_buffer.setdefault((date, hour), self._empty_input())['keys'] += 1
            self.hourly_app_stats_buffer.setdefault((date, hour, app), self._empty_app())['keys'] += 1
            key = (date, scan_code)
            self.heatmap_buffer[key] = self.heatmap_buffer.get(key, 0) + 1
            key = (date, app, scan_code)
            self.app_heatmap_buffer[key] = self.app_heatmap_buffer.get(key, 0) + 1

    def on_move(self, x, y, *, timestamp=None, monotonic_time=None, app_name=None):
        with self.lock:
            if self._paused_reasons:
                return
            (date, hour), app = self._input_context(timestamp, monotonic_time, app_name)
            if self.last_mouse_pos is not None:
                distance = math.hypot(x - self.last_mouse_pos[0], y - self.last_mouse_pos[1]) / self.px_per_mm / 1000.0
                self.hourly_input_buffer.setdefault((date, hour), self._empty_input())['distance'] += distance
                self.hourly_app_stats_buffer.setdefault((date, hour, app), self._empty_app())['distance'] += distance
            self.last_mouse_pos = (x, y)

    def on_click(self, x=0, y=0, *, timestamp=None, monotonic_time=None, app_name=None):
        with self.lock:
            if self._paused_reasons:
                return
            (date, hour), app = self._input_context(timestamp, monotonic_time, app_name)
            self.hourly_input_buffer.setdefault((date, hour), self._empty_input())['clicks'] += 1
            self.hourly_app_stats_buffer.setdefault((date, hour, app), self._empty_app())['clicks'] += 1
            bx, by = (x // 5) * 5, (y // 5) * 5
            key = (date, bx, by)
            self.mouse_heatmap_buffer[key] = self.mouse_heatmap_buffer.get(key, 0) + 1
            key = (date, app, bx, by)
            self.app_mouse_heatmap_buffer[key] = self.app_mouse_heatmap_buffer.get(key, 0) + 1

    def on_scroll(self, delta, *, timestamp=None, monotonic_time=None, app_name=None):
        with self.lock:
            if self._paused_reasons:
                return
            (date, hour), app = self._input_context(timestamp, monotonic_time, app_name)
            steps = abs(delta) / 120.0
            self.hourly_input_buffer.setdefault((date, hour), self._empty_input())['scroll'] += steps
            self.hourly_app_stats_buffer.setdefault((date, hour, app), self._empty_app())['scrolls'] += steps

    def _buffers(self):
        return (self.hourly_input_buffer, self.hourly_app_stats_buffer,
                self.heatmap_buffer, self.mouse_heatmap_buffer, self.app_heatmap_buffer,
                self.app_mouse_heatmap_buffer, self.foreground_time_buffer)

    def clear_all_data(self):
        with self.lock:
            self.db.clear_all_data()
            self._generation += 1
            for buffer in self._buffers():
                buffer.clear()
            self._metadata_pending.clear()
            self.metadata_cache.clear()
            self._app_info_cache.clear()
            self.current_foreground_app = None
            self._reset_time_unlocked(time.time())
            self._last_wall_time_observed = None
            self._last_monotonic_time_observed = None
            self.dropped_events = 0

    def set_retention_days(self, days):
        days = int(days)
        if days != -1 and not 1 <= days <= 3650:
            raise ValueError('Retention must be -1 or between 1 and 3650 days')
        with self.lock:
            self.retention_days = days
            self._last_retention_date = None
            self._apply_retention()

    def _apply_retention(self):
        with self.lock:
            today = datetime.date.today()
            if self.retention_days == -1 or self._last_retention_date == today:
                return
            cutoff = today - datetime.timedelta(days=self.retention_days - 1)
            self.db.prune_before(cutoff)
            for buffer in self._buffers():
                for key in list(buffer):
                    if key[0] < cutoff:
                        del buffer[key]
            self.metadata_cache.clear()
            self._last_retention_date = today

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


    def get_stats_snapshot(self):
        """Get a thread-safe snapshot of current buffers + DB stats."""
        with self.lock:
            today = datetime.date.today()

            # Sum today's buffered input data
            buffer_keys = 0
            buffer_clicks = 0
            buffer_distance = 0.0
            buffer_scroll = 0.0
            for (date_part, hour_part), stats in self.hourly_input_buffer.items():
                if date_part == today:
                    buffer_keys += stats['keys']
                    buffer_clicks += stats['clicks']
                    buffer_distance += stats['distance']
                    buffer_scroll += stats['scroll']

            db_stats = self.db.get_today_stats()
            if db_stats:
                # db_stats: date, key_count, mouse_click_count, mouse_distance, scroll_distance
                keys = db_stats[1] + buffer_keys
                clicks = db_stats[2] + buffer_clicks
                distance = db_stats[3] + buffer_distance
                scroll = db_stats[4] + buffer_scroll
            else:
                keys = buffer_keys
                clicks = buffer_clicks
                distance = buffer_distance
                scroll = buffer_scroll

            # Merge DB heatmap with current buffer
            db_heatmap = self.db.get_today_heatmap()
            merged_heatmap = dict(db_heatmap)
            for (date_part, key_code), count in self.heatmap_buffer.items():
                if date_part == today:
                    merged_heatmap[key_code] = merged_heatmap.get(key_code, 0) + count

            # Build buffer-only heatmap for live updates
            buffer_heatmap = {}
            for (date_part, key_code), count in self.heatmap_buffer.items():
                if date_part == today:
                    buffer_heatmap[key_code] = buffer_heatmap.get(key_code, 0) + count

            # Build buffer-only mouse heatmap for live updates
            buffer_mouse_heatmap = {}
            for (date_part, bx, by), count in self.mouse_heatmap_buffer.items():
                if date_part == today:
                    buffer_mouse_heatmap[(bx, by)] = buffer_mouse_heatmap.get((bx, by), 0) + count

            # Copy app-specific heatmap buffers (today only)
            app_heatmap_buffer_copy = {}
            for (date_part, app_name, key_code), count in self.app_heatmap_buffer.items():
                if date_part == today:
                    app_heatmap_buffer_copy.setdefault(app_name, {})[key_code] = \
                        app_heatmap_buffer_copy.get(app_name, {}).get(key_code, 0) + count

            app_mouse_heatmap_buffer_copy = {}
            for (date_part, app_name, bx, by), count in self.app_mouse_heatmap_buffer.items():
                if date_part == today:
                    app_mouse_heatmap_buffer_copy.setdefault(app_name, {})[(bx, by)] = \
                        app_mouse_heatmap_buffer_copy.get(app_name, {}).get((bx, by), 0) + count

        return {
            'keys': keys,
            'clicks': clicks,
            'distance': distance,
            'scroll': scroll,
            'heatmap': merged_heatmap,
            'mouse_heatmap': buffer_mouse_heatmap,
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


    def flush_stats(self):
        with self.lock:
            if not self._metadata_pending and not any(self._buffers()):
                return
            with self.db.transaction():
                has_input = bool(self.hourly_input_buffer)

                # Check if foreground time buffer has any non-zero values
                has_time = any(s > 0 for s in self.foreground_time_buffer.values())


                if has_input:
                    # Aggregate per-date totals for daily_stats
                    daily_totals = {}  # {date: {keys, clicks, distance, scroll}}
                    for (date_part, hour_part), stats in self.hourly_input_buffer.items():
                        dt = daily_totals.setdefault(date_part, {'keys': 0, 'clicks': 0, 'distance': 0.0, 'scroll': 0.0})
                        dt['keys'] += stats['keys']
                        dt['clicks'] += stats['clicks']
                        dt['distance'] += stats['distance']
                        dt['scroll'] += stats['scroll']

                    for date_part, dt in daily_totals.items():
                        self.db.update_stats(
                            date_part,
                            dt['keys'],
                            dt['clicks'],
                            dt['distance'],
                            dt['scroll']
                        )

                    # Per-app hourly stats
                    for (date_part, hour_part, app_name), stats in self.hourly_app_stats_buffer.items():
                        self.db.update_app_stats(date_part, app_name,
                            key_count=stats['keys'],
                            click_count=stats['clicks'],
                            scroll_count=stats['scrolls'],
                            distance=stats['distance']
                        )
                        self.db.update_hourly_app_stats(date_part, hour_part, app_name,
                            key_count=stats['keys'],
                            clicks=stats['clicks'],
                            scrolls=stats['scrolls'],
                            distance=stats['distance']
                        )

                    # Heatmap data (keyed by (date, key_code))
                    for (date_part, key_code), count in self.heatmap_buffer.items():
                        self.db.update_heatmap(date_part, key_code, count)

                    # Mouse heatmap (keyed by (date, x, y))
                    for (date_part, x, y), count in self.mouse_heatmap_buffer.items():
                        self.db.update_mouse_heatmap(date_part, x, y, count)

                    # App-specific keyboard heatmap (keyed by (date, app, key_code))
                    for (date_part, app_name, key_code), count in self.app_heatmap_buffer.items():
                        self.db.update_app_heatmap(date_part, app_name, key_code, count)

                    # App-specific mouse heatmap (keyed by (date, app, x, y))
                    for (date_part, app_name, x, y), count in self.app_mouse_heatmap_buffer.items():
                        self.db.update_app_mouse_heatmap(date_part, app_name, x, y, count)

                if has_time:
                    # Flush foreground time buffer
                    for (date_part, hour_part, app_name), seconds in self.foreground_time_buffer.items():
                        if seconds > 0:
                            self.db.update_foreground_time(date_part, hour_part, app_name, float(seconds))

                for name, (friendly, path) in self._metadata_pending.items():
                    self.db.update_app_metadata(name, friendly, path)

            self._metadata_pending.clear()
            self.last_flush_time = time.time()
            self.write_error = None
            self.hourly_input_buffer.clear()
            self.hourly_app_stats_buffer.clear()
            self.heatmap_buffer.clear()
            self.mouse_heatmap_buffer.clear()
            self.app_heatmap_buffer.clear()
            self.app_mouse_heatmap_buffer.clear()
            self.foreground_time_buffer.clear()

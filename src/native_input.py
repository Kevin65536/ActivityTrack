"""Minimal Win32 hook thread. Callbacks only copy events into the recorder queue."""
import ctypes
from ctypes import wintypes
import threading

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
LRESULT = ctypes.c_ssize_t
LPARAM = ctypes.c_ssize_t
WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0104, 0x0105
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN = 0x0201, 0x0204, 0x0207
WM_MOUSEWHEEL = 0x020A
WM_QUIT = 0x0012


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [('pt', wintypes.POINT), ('mouseData', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, LPARAM)
for function, result, arguments in (
    (user32.CallNextHookEx, LRESULT, [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, LPARAM]),
    (user32.SetWindowsHookExW, wintypes.HHOOK, [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]),
    (user32.UnhookWindowsHookEx, wintypes.BOOL, [wintypes.HHOOK]),
    (user32.GetMessageW, wintypes.BOOL, [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]),
    (user32.PeekMessageW, wintypes.BOOL, [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]),
    (user32.TranslateMessage, wintypes.BOOL, [ctypes.POINTER(wintypes.MSG)]),
    (user32.DispatchMessageW, LRESULT, [ctypes.POINTER(wintypes.MSG)]),
    (user32.PostThreadMessageW, wintypes.BOOL, [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, LPARAM]),
    (user32.GetForegroundWindow, wintypes.HWND, []),
    (kernel32.GetCurrentThreadId, wintypes.DWORD, []),
):
    function.restype = result
    function.argtypes = arguments


class NativeInputCapture:
    def __init__(self, emit):
        self.emit = emit
        self.thread = None
        self.thread_id = None
        self.keyboard_hook = None
        self.mouse_hook = None
        self.keys_held = set()
        self.last_error = None
        self.ready = threading.Event()
        self._reset_keys = threading.Event()

    def reset_held_keys(self):
        # Only the hook thread mutates keys_held while hooks are active.
        self._reset_keys.set()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.ready.clear()
        self.last_error = None
        self.thread = threading.Thread(target=self._run, name='ActivityTrack hooks', daemon=True)
        self.thread.start()
        self.ready.wait(2)

    def stop(self):
        if not self.thread or not self.thread.is_alive():
            return
        self.ready.wait(2)
        if self.thread_id and self.thread.is_alive():
            if not user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0):
                raise ctypes.WinError(ctypes.get_last_error())
        self.thread.join(5)
        if self.thread.is_alive():
            raise RuntimeError('The input hook thread did not stop')

    def keyboard_proc(self, code, message, address):
        result = user32.CallNextHookEx(self.keyboard_hook, code, message, address)
        try:
            if self._reset_keys.is_set():
                self.keys_held.clear()
                self._reset_keys.clear()
            if code >= 0:
                event = ctypes.cast(address, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                # Ignore injected input before changing held-key state.
                if not event.flags & 0x10:
                    if message in (WM_KEYDOWN, WM_SYSKEYDOWN) and event.vkCode not in self.keys_held:
                        self.keys_held.add(event.vkCode)
                        self.emit('key', (event.vkCode, event.scanCode), user32.GetForegroundWindow())
                    elif message in (WM_KEYUP, WM_SYSKEYUP):
                        self.keys_held.discard(event.vkCode)
        except Exception:
            # No logging, file access, process lookups, or recorder locks here.
            self.last_error = 'An input callback failed'
        return result

    def mouse_proc(self, code, message, address):
        result = user32.CallNextHookEx(self.mouse_hook, code, message, address)
        try:
            if code >= 0:
                event = ctypes.cast(address, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not event.flags & 0x01:  # LLMHF_INJECTED
                    if message == WM_MOUSEMOVE:
                        self.emit('move', (event.pt.x, event.pt.y), user32.GetForegroundWindow())
                    elif message in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                        self.emit('click', (event.pt.x, event.pt.y), user32.GetForegroundWindow())
                    elif message == WM_MOUSEWHEEL:
                        delta = ctypes.c_short((event.mouseData >> 16) & 0xFFFF).value
                        self.emit('scroll', (delta,), user32.GetForegroundWindow())
        except Exception:
            self.last_error = 'An input callback failed'
        return result

    def _run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        message = wintypes.MSG()
        # Establish the message queue before stop() can post WM_QUIT.
        user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        self._keyboard_callback = HOOKPROC(self.keyboard_proc)
        self._mouse_callback = HOOKPROC(self.mouse_proc)
        try:
            self.keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._keyboard_callback, None, 0)
            if not self.keyboard_hook:
                raise ctypes.WinError(ctypes.get_last_error())
            self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_callback, None, 0)
            if not self.mouse_hook:
                raise ctypes.WinError(ctypes.get_last_error())
            self.ready.set()
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0:
                    break
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self.last_error = str(error)
        finally:
            if self.keyboard_hook:
                user32.UnhookWindowsHookEx(self.keyboard_hook)
                self.keyboard_hook = None
            if self.mouse_hook:
                user32.UnhookWindowsHookEx(self.mouse_hook)
                self.mouse_hook = None
            self.ready.set()

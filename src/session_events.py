"""Translate documented Windows session/power messages into recorder controls."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter

WM_WTSSESSION_CHANGE = 0x02B1
WM_POWERBROADCAST = 0x0218


class SessionEvents(QAbstractNativeEventFilter):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.hwnd = None
        self.error = None
        self.api = ctypes.WinDLL('wtsapi32', use_last_error=True)
        self.api.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.api.WTSRegisterSessionNotification.restype = wintypes.BOOL
        self.api.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
        self.api.WTSUnRegisterSessionNotification.restype = wintypes.BOOL

    def register(self, hwnd):
        if self.hwnd:
            return
        if not self.api.WTSRegisterSessionNotification(hwnd, 0):
            self.error = str(ctypes.WinError(ctypes.get_last_error()))
            return
        self.hwnd = hwnd
        self.error = None

    def close(self):
        if self.hwnd:
            self.api.WTSUnRegisterSessionNotification(self.hwnd)
            self.hwnd = None

    def handle_message(self, message, code):
        if message == WM_WTSSESSION_CHANGE:
            states = {7: (True, 'lock'), 8: (False, 'lock'),
                      2: (True, 'disconnect'), 4: (True, 'disconnect'),
                      1: (False, 'disconnect'), 3: (False, 'disconnect'),
                      6: (True, 'logoff'), 5: (False, 'logoff')}
            if code in states:
                self.tracker.notify_session_state(*states[code])
        elif message == WM_POWERBROADCAST:
            if code == 4:
                self.tracker.notify_session_state(True, 'suspend')
            elif code in (7, 18):
                self.tracker.notify_session_state(False, 'suspend')

    def nativeEventFilter(self, event_type, address):
        if bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            message = wintypes.MSG.from_address(int(address))
            if self.hwnd and message.hWnd == self.hwnd:
                self.handle_message(message.message, message.wParam)
        return False, 0

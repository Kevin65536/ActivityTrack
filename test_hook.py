"""
Safe test script for Windows low-level hooks.
This script has a 10-second timeout and can be stopped with Ctrl+C.
"""
import ctypes
from ctypes import wintypes
import threading
import time
import sys

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_LBUTTONDOWN = 0x0201

# CRITICAL: On 64-bit Windows, LPARAM is 64-bit
# LRESULT is also 64-bit (c_longlong on 64-bit, c_long on 32-bit)
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

# CRITICAL: Use proper types for 64-bit Windows
# HOOKPROC signature: LRESULT CALLBACK HookProc(int nCode, WPARAM wParam, LPARAM lParam)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, LPARAM)

# Set proper argument and return types for CallNextHookEx
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT

class SafeHookTest:
    def __init__(self):
        self.keyboard_hook = None
        self.mouse_hook = None
        self.hook_thread_id = None
        self.key_count = 0
        self.click_count = 0
        self.running = False
        
    def keyboard_proc(self, nCode, wParam, lParam):
        """
        CRITICAL: The hook callback MUST:
        1. Return CallNextHookEx result quickly
        2. Not block or do heavy processing
        """
        # Method 1: Call next hook FIRST, then process (current approach)
        # result = user32.CallNextHookEx(self.keyboard_hook, nCode, wParam, lParam)
        # if nCode >= 0 and wParam == WM_KEYDOWN:
        #     self.key_count += 1
        #     print(f"Key pressed! Count: {self.key_count}")
        # return result
        
        # Method 2: Process first, then call next hook (original approach) 
        # This should also work if we always return properly
        if nCode >= 0 and wParam == WM_KEYDOWN:
            self.key_count += 1
            print(f"Key pressed! Count: {self.key_count}")
        return user32.CallNextHookEx(self.keyboard_hook, nCode, wParam, lParam)
    
    def mouse_proc(self, nCode, wParam, lParam):
        if nCode >= 0 and wParam == WM_LBUTTONDOWN:
            self.click_count += 1
            print(f"Mouse clicked! Count: {self.click_count}")
        return user32.CallNextHookEx(self.mouse_hook, nCode, wParam, lParam)
    
    def hook_loop(self):
        self.hook_thread_id = kernel32.GetCurrentThreadId()
        print(f"Hook thread started, ID: {self.hook_thread_id}")
        
        # IMPORTANT: Must keep reference to prevent garbage collection
        self._kb_proc = HOOKPROC(self.keyboard_proc)
        self._ms_proc = HOOKPROC(self.mouse_proc)
        
        self.keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, None, 0)
        self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._ms_proc, None, 0)
        
        if not self.keyboard_hook:
            print(f"Failed to set keyboard hook! Error: {kernel32.GetLastError()}")
            return
        if not self.mouse_hook:
            print(f"Failed to set mouse hook! Error: {kernel32.GetLastError()}")
            return
            
        print(f"Hooks installed: KB={self.keyboard_hook}, MS={self.mouse_hook}")
        print("Hooks are active. Try typing or clicking...")
        
        # Message loop - THIS IS CRITICAL
        msg = wintypes.MSG()
        while self.running:
            # Use PeekMessage with a timeout approach instead of blocking GetMessage
            # This allows us to check self.running periodically
            ret = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)  # PM_REMOVE = 1
            if ret:
                if msg.message == 0x0012:  # WM_QUIT
                    print("Received WM_QUIT")
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                # No message, sleep briefly to avoid busy loop
                time.sleep(0.01)
        
        # Cleanup
        if self.keyboard_hook:
            user32.UnhookWindowsHookEx(self.keyboard_hook)
            print("Keyboard hook removed")
        if self.mouse_hook:
            user32.UnhookWindowsHookEx(self.mouse_hook)
            print("Mouse hook removed")
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.hook_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        print("\nStopping hooks...")
        self.running = False
        if self.hook_thread_id:
            user32.PostThreadMessageW(self.hook_thread_id, 0x0012, 0, 0)  # WM_QUIT
        time.sleep(0.5)
        print(f"Final stats - Keys: {self.key_count}, Clicks: {self.click_count}")


def main():
    print("=" * 50)
    print("Safe Hook Test - Will auto-stop after 10 seconds")
    print("Press Ctrl+C to stop earlier")
    print("=" * 50)
    
    tester = SafeHookTest()
    tester.start()
    
    try:
        # Give hooks time to install
        time.sleep(0.5)
        
        # Run for 10 seconds max
        for i in range(10, 0, -1):
            print(f"\rTime remaining: {i}s ", end="", flush=True)
            time.sleep(1)
        print()
        
    except KeyboardInterrupt:
        print("\nCtrl+C detected")
    finally:
        tester.stop()
    
    print("Test completed!")

if __name__ == "__main__":
    main()

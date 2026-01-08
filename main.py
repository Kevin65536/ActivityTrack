import sys
import signal
import os
import faulthandler
import traceback
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
from src.tracker import ActivityTrack
from src.ui.main_window import MainWindow
from src.ui.tray_icon import TrayIcon
from src.config import Config
from src.break_reminder import BreakReminder


def _load_app_icon():
    """Load the application icon for windows and taskbar."""
    icon_paths = []

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        icon_paths.append(os.path.join(sys._MEIPASS, "resources", "icon.ico"))
    else:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        icon_paths.append(os.path.join(base_dir, "resources", "icon.ico"))
        icon_paths.append(os.path.join(os.path.dirname(base_dir), "resources", "icon.ico"))

    for path in icon_paths:
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon

    return QIcon()

def main():
    # Crash/exception diagnostics: dump tracebacks on fatal errors and uncaught exceptions
    # Note: faulthandler requires sys.stderr, which is None when console=False in PyInstaller
    if sys.stderr is not None:
        try:
            faulthandler.enable(all_threads=True)
        except Exception:
            pass  # Silently ignore if faulthandler fails

    def log_exception(exc_type, exc_value, exc_tb):
        # When packaged without console, stderr might be None
        if sys.stderr is not None:
            print("[FATAL] Unhandled exception:", exc_type.__name__, exc_value, file=sys.stderr)
            traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = log_exception

    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Set Windows AppUserModelID so the taskbar uses our icon instead of the default python icon
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ActivityTrack")
    except Exception:
        pass
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    app_icon = _load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    
    skip_tracker = os.environ.get("SKIP_TRACKER", "0") == "1"
    if skip_tracker:
        print("[WARN] SKIP_TRACKER=1 -> tracker is DISABLED for diagnostics")
        tracker = ActivityTrack()
    else:
        tracker = ActivityTrack()
        tracker.start()
    
    # Initialize config
    config = Config()
    
    # Sync autostart state between config file and registry
    # This ensures UI reflects the actual registry state
    config.sync_autostart_state()
    
    # Initialize UI
    window = MainWindow(tracker, config)
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    tray = TrayIcon()
    
    # Initialize break reminder
    break_reminder = BreakReminder(tracker, config)
    
    # Set up notification callback using tray icon
    def show_break_notification(title, message):
        """Show a Windows notification via the system tray icon."""
        if config.show_notifications:
            tray.showMessage(title, message, tray.MessageIcon.Information, 10000)
    
    break_reminder.set_notification_callback(show_break_notification)
    break_reminder.start()
    
    # Connect settings change to break reminder
    def on_settings_changed():
        # Break reminder will pick up new config values automatically
        # since it reads from config on each check
        pass
    
    window.settings_tab.settings_changed.connect(on_settings_changed)
    
    # Connect signals
    tray.show_window_signal.connect(window.show)
    tray.show_window_signal.connect(window.activateWindow)
    
    def quit_app():
        break_reminder.stop()
        if not skip_tracker:
            tracker.stop()
        app.quit()
        
    tray.quit_signal.connect(quit_app)
    
    # Show window initially
    window.show()
    
    # Allow python to handle signals by letting the event loop wake up periodically
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

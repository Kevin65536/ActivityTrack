import sys
import signal
from PySide6.QtWidgets import QApplication
from src.tracker import InputTracker
from src.ui.main_window import MainWindow
from src.ui.tray_icon import TrayIcon
from src.ui.overlay import OverlayWindow
from PySide6.QtCore import QObject, Signal, Slot, QTimer

class Bridge(QObject):
    key_pressed = Signal()

def main():
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    bridge = Bridge()
    
    # Initialize Tracker
    tracker = InputTracker(on_key_press_callback=bridge.key_pressed.emit)
    tracker.start()
    
    # Initialize UI
    window = MainWindow(tracker)
    tray = TrayIcon()
    overlay = OverlayWindow()
    overlay.show()
    
    bridge.key_pressed.connect(overlay.on_key_press)
    
    # Connect signals
    tray.show_window_signal.connect(window.show)
    tray.show_window_signal.connect(window.activateWindow)
    
    def quit_app():
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

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Signal

class TrayIcon(QSystemTrayIcon):
    show_window_signal = Signal()
    quit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("icon.png")) # Placeholder, need an icon
        self.setVisible(True)
        
        # Create menu
        self.menu = QMenu()
        
        self.show_action = QAction("Show Dashboard", self)
        self.show_action.triggered.connect(self.show_window_signal.emit)
        self.menu.addAction(self.show_action)
        
        self.menu.addSeparator()
        
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quit_signal.emit)
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        
        self.activated.connect(self.on_activated)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_signal.emit()

import os
import sys
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush
from PySide6.QtCore import Signal, Qt

class TrayIcon(QSystemTrayIcon):
    show_window_signal = Signal()
    quit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load icon from file, fallback to programmatic icon
        self.setIcon(self._load_icon())
        self.setVisible(True)
        self.setToolTip("ActivityTrack")
        
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
    
    def _load_icon(self):
        """Load icon from file, fallback to default icon if not found."""
        # Try multiple paths for icon file
        icon_paths = []
        
        # For PyInstaller bundled app
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle - icon is in _internal/resources/
            base_path = sys._MEIPASS
            icon_paths.append(os.path.join(base_path, 'resources', 'icon.ico'))
        else:
            # Development mode - try relative paths
            icon_paths.append('resources/icon.ico')
            icon_paths.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'icon.ico'))
        
        # Try to load from each path
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    return icon
        
        # Fallback to programmatic icon
        return self._create_default_icon()
    
    def _create_default_icon(self):
        """Create a simple icon programmatically."""
        # Create a 64x64 pixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw green circle background
        painter.setBrush(QBrush(QColor(0, 230, 118)))  # #00e676
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        
        # Draw "K" letter
        painter.setPen(QColor(30, 30, 30))
        font = painter.font()
        font.setPixelSize(36)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "K")
        
        painter.end()
        
        return QIcon(pixmap)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_signal.emit()

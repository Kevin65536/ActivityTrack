from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush
from PySide6.QtCore import Signal, Qt

class TrayIcon(QSystemTrayIcon):
    show_window_signal = Signal()
    quit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create a simple icon programmatically (green circle with K letter)
        self.setIcon(self._create_default_icon())
        self.setVisible(True)
        self.setToolTip("InputTracker")
        
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

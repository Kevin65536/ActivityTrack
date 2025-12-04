from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QColor, QPainter

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Full screen overlay
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        
        self.combo_count = 0
        self.combo_label = QLabel(self)
        self.combo_label.setAlignment(Qt.AlignCenter)
        self.combo_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.combo_label.setStyleSheet("color: #00FF00; background-color: transparent;")
        self.combo_label.hide()
        
        # Position combo counter in top right or somewhere visible
        self.combo_label.resize(200, 100)
        self.combo_label.move(screen_geo.width() - 250, 50)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.reset_combo)
        self.timer.setSingleShot(True)
        
        self.shake_anim = QPropertyAnimation(self.combo_label, b"pos")
        self.shake_anim.setDuration(100)
        self.shake_anim.setEasingCurve(QEasingCurve.InOutBounce)

    def on_key_press(self):
        self.combo_count += 1
        self.combo_label.setText(f"{self.combo_count} COMBO!")
        self.combo_label.show()
        self.combo_label.adjustSize()
        
        # Reset timer
        self.timer.start(2000) # 2 seconds to keep combo
        
        # Shake effect
        base_pos = QPoint(self.width() - 250, 50)
        self.shake_anim.stop()
        self.shake_anim.setStartValue(base_pos)
        self.shake_anim.setEndValue(base_pos + QPoint(5, 5))
        self.shake_anim.setKeyValueAt(0.5, base_pos - QPoint(5, 5))
        self.shake_anim.setEndValue(base_pos)
        self.shake_anim.start()

    def reset_combo(self):
        self.combo_count = 0
        self.combo_label.hide()

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt

# Standard US keyboard layout with scan codes
# Format: (scan_code, label, row, col, width)
# Width is in key units (1 = standard key width)
KEYBOARD_LAYOUT = [
    # Row 0: Function keys
    (0x01, "Esc", 0, 0, 1),
    (0x3B, "F1", 0, 2, 1), (0x3C, "F2", 0, 3, 1), (0x3D, "F3", 0, 4, 1), (0x3E, "F4", 0, 5, 1),
    (0x3F, "F5", 0, 6.5, 1), (0x40, "F6", 0, 7.5, 1), (0x41, "F7", 0, 8.5, 1), (0x42, "F8", 0, 9.5, 1),
    (0x43, "F9", 0, 11, 1), (0x44, "F10", 0, 12, 1), (0x57, "F11", 0, 13, 1), (0x58, "F12", 0, 14, 1),
    
    # Row 1: Number row
    (0x29, "`", 1, 0, 1),
    (0x02, "1", 1, 1, 1), (0x03, "2", 1, 2, 1), (0x04, "3", 1, 3, 1), (0x05, "4", 1, 4, 1),
    (0x06, "5", 1, 5, 1), (0x07, "6", 1, 6, 1), (0x08, "7", 1, 7, 1), (0x09, "8", 1, 8, 1),
    (0x0A, "9", 1, 9, 1), (0x0B, "0", 1, 10, 1), (0x0C, "-", 1, 11, 1), (0x0D, "=", 1, 12, 1),
    (0x0E, "Back", 1, 13, 2),
    
    # Row 2: QWERTY row
    (0x0F, "Tab", 2, 0, 1.5),
    (0x10, "Q", 2, 1.5, 1), (0x11, "W", 2, 2.5, 1), (0x12, "E", 2, 3.5, 1), (0x13, "R", 2, 4.5, 1),
    (0x14, "T", 2, 5.5, 1), (0x15, "Y", 2, 6.5, 1), (0x16, "U", 2, 7.5, 1), (0x17, "I", 2, 8.5, 1),
    (0x18, "O", 2, 9.5, 1), (0x19, "P", 2, 10.5, 1), (0x1A, "[", 2, 11.5, 1), (0x1B, "]", 2, 12.5, 1),
    (0x2B, "\\", 2, 13.5, 1.5),
    
    # Row 3: Home row
    (0x3A, "Caps", 3, 0, 1.75),
    (0x1E, "A", 3, 1.75, 1), (0x1F, "S", 3, 2.75, 1), (0x20, "D", 3, 3.75, 1), (0x21, "F", 3, 4.75, 1),
    (0x22, "G", 3, 5.75, 1), (0x23, "H", 3, 6.75, 1), (0x24, "J", 3, 7.75, 1), (0x25, "K", 3, 8.75, 1),
    (0x26, "L", 3, 9.75, 1), (0x27, ";", 3, 10.75, 1), (0x28, "'", 3, 11.75, 1),
    (0x1C, "Enter", 3, 12.75, 2.25),
    
    # Row 4: Shift row
    (0x2A, "Shift", 4, 0, 2.25),
    (0x2C, "Z", 4, 2.25, 1), (0x2D, "X", 4, 3.25, 1), (0x2E, "C", 4, 4.25, 1), (0x2F, "V", 4, 5.25, 1),
    (0x30, "B", 4, 6.25, 1), (0x31, "N", 4, 7.25, 1), (0x32, "M", 4, 8.25, 1), (0x33, ",", 4, 9.25, 1),
    (0x34, ".", 4, 10.25, 1), (0x35, "/", 4, 11.25, 1),
    (0x36, "Shift", 4, 12.25, 2.75),
    
    # Row 5: Control row
    (0x1D, "Ctrl", 5, 0, 1.25),
    (0x5B, "Win", 5, 1.25, 1.25),
    (0x38, "Alt", 5, 2.5, 1.25),
    (0x39, "Space", 5, 3.75, 6.25),
    (0x138, "Alt", 5, 10, 1.25),
    (0x15B, "Win", 5, 11.25, 1.25),
    (0x15D, "Menu", 5, 12.5, 1.25),
    (0x11D, "Ctrl", 5, 13.75, 1.25),
]


def get_heat_color(ratio):
    """Get color based on heat ratio (0.0 to 1.0). Blue -> Green -> Yellow -> Red."""
    if ratio < 0.25:
        # Blue to Cyan
        r = 0
        g = int(255 * (ratio / 0.25))
        b = 255
    elif ratio < 0.5:
        # Cyan to Green
        r = 0
        g = 255
        b = int(255 * (1 - (ratio - 0.25) / 0.25))
    elif ratio < 0.75:
        # Green to Yellow
        r = int(255 * ((ratio - 0.5) / 0.25))
        g = 255
        b = 0
    else:
        # Yellow to Red
        r = 255
        g = int(255 * (1 - (ratio - 0.75) / 0.25))
        b = 0
    return QColor(r, g, b)


class HeatmapWidget(QWidget):
    def __init__(self, data=None):
        super().__init__()
        self.data = data or {}
        self.setMinimumSize(800, 300)
        self.key_size = 45
        self.key_spacing = 3
        self.margin = 20

    def update_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if not self.data:
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "Start typing to see heatmap...")
            return
        
        max_count = max(self.data.values()) if self.data else 1
        
        for scan_code, label, row, col, width in KEYBOARD_LAYOUT:
            x = self.margin + col * (self.key_size + self.key_spacing)
            y = self.margin + row * (self.key_size + self.key_spacing)
            w = width * self.key_size + (width - 1) * self.key_spacing
            h = self.key_size
            
            # Get heat level
            count = self.data.get(scan_code, 0)
            if count > 0 and max_count > 0:
                ratio = min(count / max_count, 1.0)
                bg_color = get_heat_color(ratio)
            else:
                bg_color = QColor(60, 60, 60)
            
            # Draw key background
            painter.setBrush(bg_color)
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawRoundedRect(int(x), int(y), int(w), int(h), 5, 5)
            
            # Draw label
            if count > 0:
                painter.setPen(QColor(0, 0, 0))  # Dark text on colored bg
            else:
                painter.setPen(QColor(180, 180, 180))  # Light text on dark bg
            
            font = QFont("Arial", 9 if len(label) > 2 else 11)
            painter.setFont(font)
            painter.drawText(int(x), int(y), int(w), int(h), Qt.AlignCenter, label)
            
            # Draw count if non-zero
            if count > 0:
                painter.setFont(QFont("Arial", 7))
                painter.drawText(int(x + 2), int(y + h - 12), str(count))

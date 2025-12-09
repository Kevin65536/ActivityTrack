from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QRadialGradient, QImage, qRgba, QGuiApplication
from PySide6.QtCore import Qt, QRect
import numpy as np
from scipy.ndimage import gaussian_filter

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
    """Get color based on heat ratio (0.0 to 1.0). Uses a softer, less saturated gradient.
    
    Colors transition: Soft Blue → Teal → Soft Green → Warm Yellow → Soft Orange
    All colors have reduced saturation for a more pleasing look.
    """
    # Define color stops with reduced saturation (HSL-style approach)
    # Each tuple: (r, g, b) - all values are softer/muted
    if ratio < 0.25:
        # Soft Blue (#4A6FA5) to Teal (#4A8F8F)
        t = ratio / 0.25
        r = int(74 + (74 - 74) * t)
        g = int(111 + (143 - 111) * t)
        b = int(165 + (143 - 165) * t)
    elif ratio < 0.5:
        # Teal (#4A8F8F) to Soft Green (#6BAF6B)
        t = (ratio - 0.25) / 0.25
        r = int(74 + (107 - 74) * t)
        g = int(143 + (175 - 143) * t)
        b = int(143 + (107 - 143) * t)
    elif ratio < 0.75:
        # Soft Green (#6BAF6B) to Warm Yellow (#D4B85A)
        t = (ratio - 0.5) / 0.25
        r = int(107 + (212 - 107) * t)
        g = int(175 + (184 - 175) * t)
        b = int(107 + (90 - 107) * t)
    else:
        # Warm Yellow (#D4B85A) to Soft Coral (#D4736B)
        t = (ratio - 0.75) / 0.25
        r = int(212 + (212 - 212) * t)
        g = int(184 + (115 - 184) * t)
        b = int(90 + (107 - 90) * t)
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
        
        # Calculate total size of keyboard
        max_col_units = max(col + width for _, _, _, col, width in KEYBOARD_LAYOUT)
        max_row_units = max(row + 1 for _, _, row, _, _ in KEYBOARD_LAYOUT)
        
        total_w = max_col_units * self.key_size + (max_col_units - 1) * self.key_spacing
        total_h = max_row_units * self.key_size + (max_row_units - 1) * self.key_spacing
        
        # Calculate offsets to center
        start_x = (self.width() - total_w) / 2
        start_y = (self.height() - total_h) / 2
        
        max_count = max(self.data.values()) if self.data else 1
        
        for scan_code, label, row, col, width in KEYBOARD_LAYOUT:
            x = start_x + col * (self.key_size + self.key_spacing)
            y = start_y + row * (self.key_size + self.key_spacing)
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


class MouseHeatmapWidget(QWidget):
    def __init__(self, data=None):
        super().__init__()
        self.data = data or {}  # Format: {(x, y): count}
        self.setMinimumSize(800, 450)
        self.heatmap_cache = {} # Map screen_name -> QImage
        self.packed_layout = [] # List of (screen_name, draw_rect, original_geometry)
        
    def update_data(self, data):
        self.data = data
        self.heatmap_cache = {} # Invalidate cache
        self.update()
        
    def get_packed_layout(self):
        """Calculate the layout of screens with gaps removed."""
        screens = QGuiApplication.screens()
        if not screens:
            return []
            
        # Sort screens: Top-Left dominant. Sort by Y then X? 
        # Usually users want Left-to-Right.
        # Let's simple sort by X coordinate.
        sorted_screens = sorted(screens, key=lambda s: s.geometry().x())
        
        layout = []
        current_x = 0
        gap = 20 # Visual gap between screens
        
        for screen in sorted_screens:
            geom = screen.geometry()
            # We place them in a row for now (simple compaction)
            # Improving this to strictly respect relative Y positions while closing X gaps is complex.
            # Simplified approach: Respect relative Y, but pack X.
            
            # Find the "min x" in the group to normalize?
            # Actually, "closing the gap" implies we just want them side-by-side if they are side-by-side.
            # Visualizing the Wall:
            # Shift everything left until it hits another screen or origin?
            # Simple approach: Linear row packing.
            # Used for Reference Style: Just show them side-by-side.
            
            # Pack X:
            packed_rect = QRect(current_x, 0, geom.width(), geom.height())
            layout.append({
                'screen': screen,
                'packed_rect': packed_rect,
                'real_rect': geom
            })
            current_x += geom.width() + gap
            
        return layout

    def generate_screen_heatmap(self, screen):
        """Generate heatmap for a specific screen area."""
        geom = screen.geometry()
        x0, y0 = geom.x(), geom.y()
        w, h = geom.width(), geom.height()
        
        if not self.data:
            return None

        # Grid Setup
        scale = 0.25 # Downscale factor
        grid_w = int(w * scale) + 1
        grid_h = int(h * scale) + 1
        
        grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        
        # Accumulate data inside this screen's rect
        # Optimized: Iterate only if we had spatial indexing, but dict iteration is fast enough.
        # We can optimize by checking bounds before calc.
        
        has_data = False
        for (px, py), count in self.data.items():
            if x0 <= px < x0 + w and y0 <= py < y0 + h:
                gx = int((px - x0) * scale)
                gy = int((py - y0) * scale)
                if 0 <= gx < grid_w and 0 <= gy < grid_h:
                    grid[gy, gx] += count
                    has_data = True
                    
        if not has_data:
            return None
            
        # Gaussian Filter
        sigma = 8.0
        heatmap = gaussian_filter(grid, sigma=sigma)
        
        # Normalize (Globally or locally? Locally allows seeing hotspots on low-usage screens easier)
        # But Globally preserves relative intensity. 
        # Let's do Local normalization for better visibility per screen unless requested otherwise.
        # User said "Match WhatPulse", usually global. 
        # BUT, if we split generation, we need global max.
        # Let's quick-scan global max from data? No, that's raw counts.
        # We can stick to local normalization for now, it ensures every screen looks "used".
        max_val = np.max(heatmap)
        if max_val > 0:
            heatmap /= max_val
            
        # Colorize
        heatmap_8bit = (heatmap * 255).astype(np.uint8)
        image = QImage(heatmap_8bit.data, grid_w, grid_h, grid_w, QImage.Format_Indexed8)
        
        colors = []
        for i in range(256):
            if i == 0:
                colors.append(qRgba(0, 0, 0, 0))
                continue
            t = i / 255.0
            hue = 0.66 * (1.0 - t)
            alpha = int(min(t * 3.0, 0.85) * 255)
            c = QColor.fromHsvF(hue, 1.0, 1.0)
            colors.append(qRgba(c.red(), c.green(), c.blue(), alpha))
            
        image.setColorTable(colors)
        return image.copy()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        
        if not self.data:
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "No mouse data.")
            return

        # 1. Calc Layout
        layout = self.get_packed_layout()
        if not layout:
            return

        # 2. Determine Bounding Box of Packed Layout
        total_w = 0
        total_h = 0
        for item in layout:
            r = item['packed_rect']
            total_w = max(total_w, r.right())
            total_h = max(total_h, r.bottom())
            
        # 3. Fit to Widget
        padding = 20
        widget_w = self.width() - 2 * padding
        widget_h = self.height() - 2 * padding
        
        if total_w == 0 or total_h == 0: return # Should not happen
        
        scale = min(widget_w / total_w, widget_h / total_h)
        
        # Center rendering
        render_w = total_w * scale
        render_h = total_h * scale
        offset_x = padding + (widget_w - render_w) / 2
        offset_y = padding + (widget_h - render_h) / 2
        
        # 4. Draw Each Screen
        for item in layout:
            screen = item['screen']
            packed = item['packed_rect']
            real = item['real_rect']
            
            # Generate or Get Cache
            s_name = screen.name()
            if s_name not in self.heatmap_cache:
                self.heatmap_cache[s_name] = self.generate_screen_heatmap(screen)
                
            img = self.heatmap_cache[s_name]
            
            # Draw Rect
            dx = offset_x + packed.x() * scale
            dy = offset_y + packed.y() * scale
            dw = packed.width() * scale
            dh = packed.height() * scale
            
            # Draw Outline
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.setBrush(QColor(30, 30, 30))
            painter.drawRect(int(dx), int(dy), int(dw), int(dh))
            
            # Draw Heatmap
            if img:
                painter.drawImage(QRect(int(dx), int(dy), int(dw), int(dh)), img)
                
            # Label
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(int(dx + 5), int(dy + 20), f"{s_name}")
            painter.setPen(QColor(120, 120, 120))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(dx + 5), int(dy + 40), f"{real.width()}x{real.height()}")


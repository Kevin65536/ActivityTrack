from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import math
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ..i18n import tr

# Color palette for pie slices (visually distinct, pleasant colors)
PIE_COLORS = [
    "#00e676",  # Green
    "#42a5f5",  # Blue
    "#ffa726",  # Orange
    "#ab47bc",  # Purple
    "#ef5350",  # Red
    "#26c6da",  # Cyan
    "#ffee58",  # Yellow
    "#8d6e63",  # Brown
    "#66bb6a",  # Light Green
    "#7e57c2",  # Deep Purple
    "#ff7043",  # Deep Orange
    "#29b6f6",  # Light Blue
]


class PieChartWidget(QWidget):
    """A pie chart widget backed by matplotlib (more stable than custom QPainter)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metric = 'keys'
        self.data = []  # list of (label, value)
        self.font_family = "Microsoft YaHei"
        self.fig = Figure(figsize=(4, 4), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setMinimumSize(360, 360)

    def set_metric(self, metric):
        self.metric = metric

    def update_data(self, app_data, metadata=None):
        # Guard against None
        app_data = app_data or []
        metadata = metadata or {}
        print(f"[DEBUG] PieChartWidget.update_data: received {len(app_data)} items")

        metric_idx = {'keys': 1, 'clicks': 2, 'scrolls': 3, 'distance': 4}
        idx = metric_idx.get(self.metric, 1)

        items = []
        for row in app_data:
            app_name = row[0]
            value = row[idx] or 0
            if value > 0:
                label = metadata.get(app_name, {}).get('friendly_name') or (app_name[:-4] if app_name.lower().endswith('.exe') else app_name)
                items.append((label, value))

        items.sort(key=lambda x: x[1], reverse=True)
        if len(items) > 6:
            top = items[:6]
            others = sum(v for _, v in items[6:])
            if others > 0:
                top.append((tr('apps.others'), others))
            items = top

        self.data = items
        self._draw_chart()

    def _draw_chart(self):
        self.ax.clear()
        self.fig.patch.set_facecolor('#1e1e1e')
        self.ax.set_facecolor('#1e1e1e')

        if not self.data:
            self.ax.text(0.5, 0.5, tr('apps.no_data'), color='white', ha='center', va='center', fontsize=12)
            self.ax.axis('off')
            self.canvas.draw_idle()
            return

        labels = [l for l, _ in self.data]
        values = [v for _, v in self.data]
        colors = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(values))]

        total = sum(values)
        # Margins for leader lines
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Use autopct to add percentage labels directly
        wedges, texts, autotexts = self.ax.pie(
            values,
            labels=None,
            colors=colors,
            startangle=90,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 2 else '',
            wedgeprops={'width': 0.4, 'edgecolor': '#1e1e1e', 'linewidth': 1.5},
            counterclock=False,
            pctdistance=0.75,
            textprops={'color': 'white', 'fontsize': 8, 'fontweight': 'bold'}
        )

        # Center total text
        if self.metric == 'distance':
            total_text = f"{total:.1f} m"
        else:
            total_text = f"{int(total):,}"
        self.ax.text(0, 0, total_text, ha='center', va='center', color='white',
                      fontsize=13, fontweight='bold', fontname=self.font_family)

        # Collect label information and group by side
        label_info = []
        for wedge, (label, value), color in zip(wedges, self.data, colors):
            pct = (value / total) * 100 if total else 0
            angle = (wedge.theta2 + wedge.theta1) / 2.0
            theta = math.radians(angle)
            
            x_wedge = 1.0 * math.cos(theta)
            y_wedge = 1.0 * math.sin(theta)
            
            label_info.append({
                'label': label,
                'pct': pct,
                'color': color,
                'theta': theta,
                'x_wedge': x_wedge,
                'y_wedge': y_wedge,
                'on_right': x_wedge >= 0
            })
        
        # Separate left and right, sort by y position (top to bottom)
        left_labels = sorted([l for l in label_info if not l['on_right']], 
                           key=lambda x: -x['y_wedge'])
        right_labels = sorted([l for l in label_info if l['on_right']], 
                            key=lambda x: -x['y_wedge'])
        
        def adjust_positions_no_overlap(labels_side):
            """Adjust y positions to avoid overlap while maintaining order"""
            if not labels_side:
                return []
            
            min_spacing = 0.15  # Minimum vertical spacing between labels
            
            # Start with wedge y positions
            positions = [l['y_wedge'] for l in labels_side]
            
            # Adjust to avoid overlaps (downward pass)
            for i in range(1, len(positions)):
                if positions[i] > positions[i-1] - min_spacing:
                    positions[i] = positions[i-1] - min_spacing
            
            # Clamp to bounds and adjust upward if needed
            max_y = 1.1
            min_y = -1.1
            
            # First pass: clamp bottom
            if positions[-1] < min_y:
                offset = min_y - positions[-1]
                positions = [p + offset for p in positions]
            
            # Second pass: clamp top
            if positions[0] > max_y:
                offset = positions[0] - max_y
                positions = [p - offset for p in positions]
            
            return positions
        
        def draw_labels_side(labels_side, x_text_pos):
            """Draw labels on one side with smart positioning to avoid crossings"""
            if not labels_side:
                return
            
            y_positions = adjust_positions_no_overlap(labels_side)
            
            for i, info in enumerate(labels_side):
                # Start: edge of wedge
                x_start = info['x_wedge']
                y_start = info['y_wedge']
                
                # Elbow: radial extension
                elbow_radius = 1.08
                x_elbow = elbow_radius * math.cos(info['theta'])
                y_elbow = elbow_radius * math.sin(info['theta'])
                
                # End: text position (adjusted to avoid overlap)
                y_text = y_positions[i]
                
                # Draw two-segment line
                self.ax.plot(
                    [x_start, x_elbow], [y_start, y_elbow],
                    color=info['color'], linewidth=1.0, alpha=0.7, zorder=1
                )
                self.ax.plot(
                    [x_elbow, x_text_pos], [y_elbow, y_text],
                    color=info['color'], linewidth=1.0, alpha=0.7, zorder=1
                )
                
                # Add text
                self.ax.text(
                    x_text_pos, y_text,
                    info['label'],
                    ha='left' if x_text_pos > 0 else 'right',
                    va='center',
                    color='#e0e0e0',
                    fontsize=9,
                    fontfamily=self.font_family,
                    clip_on=False,
                    zorder=11
                )
        
        # Draw left and right sides
        draw_labels_side(left_labels, -1.25)
        draw_labels_side(right_labels, 1.25)

        # Preserve aspect and keep space for labels
        self.ax.axis('equal')
        self.ax.set_xlim(-1.6, 1.6)
        self.ax.set_ylim(-1.4, 1.4)
        self.canvas.draw_idle()


class AppPieChartWidget(QWidget):
    """Container widget for pie chart (metric selector moved to main header)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cached_data = []
        self._cached_metadata = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Just the pie chart, no metric selector here
        self.pie_chart = PieChartWidget()
        layout.addWidget(self.pie_chart, 1)
    
    def set_metric(self, metric):
        """Set the metric from external control."""
        self.pie_chart.set_metric(metric)
        
    def update_data(self, app_data, metadata=None):
        """Update pie chart data."""
        self._cached_data = app_data
        self._cached_metadata = metadata
        self.pie_chart.update_data(app_data, metadata)
        
    def refresh_display(self):
        """Refresh display with cached data (used when metric changes)."""
        if self._cached_data:
            self.pie_chart.update_data(self._cached_data, self._cached_metadata)

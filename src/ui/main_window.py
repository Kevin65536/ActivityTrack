from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame, QGridLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QColor, QPalette
from .utils import HeatmapWidget

class StatCard(QFrame):
    def __init__(self, title, value, unit=""):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Arial", 12))
        self.lbl_title.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(self.lbl_title)
        
        self.lbl_value = QLabel(f"{value} {unit}")
        self.lbl_value.setFont(QFont("Arial", 24, QFont.Bold))
        self.lbl_value.setStyleSheet("color: #00e676;")
        layout.addWidget(self.lbl_value)
        
        self.unit = unit

    def update_value(self, value):
        self.lbl_value.setText(f"{value} {self.unit}")

class MainWindow(QMainWindow):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.setWindowTitle("Input Tracker")
        self.resize(1000, 700)
        
        # Dark Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                background: #2b2b2b;
                color: #aaaaaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #3d3d3d;
                color: #ffffff;
            }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Dashboard Tab
        self.dashboard_tab = QWidget()
        self.setup_dashboard()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # Heatmap Tab
        self.heatmap_tab = QWidget()
        self.setup_heatmap()
        self.tabs.addTab(self.heatmap_tab, "Heatmap")
        
        # Timer to update UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000) # Update every second
        
        # Initial update
        self.update_stats()

    def setup_dashboard(self):
        layout = QVBoxLayout(self.dashboard_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Today's Statistics")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        # Cards Grid
        grid = QGridLayout()
        grid.setSpacing(20)
        
        self.card_keys = StatCard("Keystrokes", 0)
        self.card_clicks = StatCard("Mouse Clicks", 0)
        self.card_distance = StatCard("Mouse Distance", 0.0, "m")
        self.card_scroll = StatCard("Scroll Distance", 0, "steps")
        
        grid.addWidget(self.card_keys, 0, 0)
        grid.addWidget(self.card_clicks, 0, 1)
        grid.addWidget(self.card_distance, 1, 0)
        grid.addWidget(self.card_scroll, 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()

    def setup_heatmap(self):
        layout = QVBoxLayout(self.heatmap_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heatmap_widget = HeatmapWidget()
        layout.addWidget(self.heatmap_widget)

    def update_stats(self):
        # Get snapshot from tracker
        stats = self.tracker.get_stats_snapshot()
        
        # Update Cards
        self.card_keys.update_value(f"{stats['keys']:,}")
        self.card_clicks.update_value(f"{stats['clicks']:,}")
        self.card_distance.update_value(f"{stats['distance']:.2f}")
        self.card_scroll.update_value(f"{stats['scroll']:.0f}")
        
        # Update Heatmap
        # We need to merge DB heatmap data with current buffer if we want full history
        # For now, let's just show what's in the snapshot (which includes buffer)
        # BUT, the snapshot only has the buffer. We need to fetch DB stats for heatmap too.
        # This is expensive to do every second. 
        # Better approach: Fetch DB once on load, and then add buffer.
        # For now, let's just pass the buffer + a cached DB version.
        
        # Ideally, tracker.get_stats_snapshot() should return merged heatmap data?
        # Or we just show the session data in heatmap for responsiveness.
        # Let's show session data (buffer) for now to be safe and fast.
        
        # Wait, the user wants to see "heatmap". Usually that means "today's heatmap".
        # Let's fetch today's heatmap from DB occasionally or cache it.
        # For simplicity in this iteration: just show buffer. 
        # IMPROVEMENT: Fetch DB heatmap in tracker.get_stats_snapshot? No, too slow.
        
        self.heatmap_widget.update_data(stats['heatmap'])

    def closeEvent(self, event):
        event.ignore()
        self.hide()

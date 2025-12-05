from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QTabWidget, QFrame, QGridLayout, QPushButton,
                                QButtonGroup, QSizePolicy)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from .utils import HeatmapWidget
from .history_chart import HistoryChartWidget
import datetime


class TimeRangeSelector(QWidget):
    """Button bar for selecting time range: Today, Week, Month, Year, All"""
    range_changed = Signal(str)  # Emits: 'today', 'week', 'month', 'year', 'all'
    
    def __init__(self):
        super().__init__()
        self.current_range = 'today'
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.buttons = {}
        ranges = [
            ('today', 'Today'),
            ('week', 'Week'),
            ('month', 'Month'),
            ('year', 'Year'),
            ('all', 'All Time')
        ]
        
        for key, label in ranges:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, k=key: self.on_range_selected(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        
        # Select 'today' by default
        self.buttons['today'].setChecked(True)
        
        layout.addStretch()
        
        # Apply styling
        self.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #aaaaaa;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:checked {
                background-color: #00e676;
                color: #1e1e1e;
                font-weight: bold;
            }
        """)
    
    def on_range_selected(self, key):
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)
        self.current_range = key
        self.range_changed.emit(key)
    
    def get_date_range(self):
        """Returns (start_date, end_date) based on current selection."""
        today = datetime.date.today()
        if self.current_range == 'today':
            return today, today
        elif self.current_range == 'week':
            return today - datetime.timedelta(days=6), today
        elif self.current_range == 'month':
            return today - datetime.timedelta(days=29), today
        elif self.current_range == 'year':
            return today - datetime.timedelta(days=364), today
        else:  # 'all'
            return None, None


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
        
        # History Tab
        self.history_tab = QWidget()
        self.setup_history()
        self.tabs.addTab(self.history_tab, "History")
        
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
        
        # Header with Title and Time Range Selector
        header = QHBoxLayout()
        
        self.dashboard_title = QLabel("Today's Statistics")
        self.dashboard_title.setFont(QFont("Arial", 28, QFont.Bold))
        self.dashboard_title.setStyleSheet("color: white;")
        header.addWidget(self.dashboard_title)
        
        header.addStretch()
        
        self.time_selector = TimeRangeSelector()
        self.time_selector.range_changed.connect(self.on_time_range_changed)
        header.addWidget(self.time_selector)
        
        layout.addLayout(header)
        
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
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with Title and Time Range Selector (matching Dashboard layout)
        header = QHBoxLayout()
        
        self.heatmap_title = QLabel("Keyboard Heatmap")
        self.heatmap_title.setFont(QFont("Arial", 28, QFont.Bold))
        self.heatmap_title.setStyleSheet("color: white;")
        header.addWidget(self.heatmap_title)
        
        header.addStretch()
        
        self.heatmap_time_selector = TimeRangeSelector()
        self.heatmap_time_selector.range_changed.connect(self.on_heatmap_range_changed)
        header.addWidget(self.heatmap_time_selector)
        
        layout.addLayout(header)
        
        self.heatmap_widget = HeatmapWidget()
        layout.addWidget(self.heatmap_widget)
        layout.addStretch()

    def setup_history(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.history_chart = HistoryChartWidget(self.tracker.db)
        layout.addWidget(self.history_chart)

    def on_time_range_changed(self, range_key):
        """Handle time range selection change in dashboard."""
        titles = {
            'today': "Today's Statistics",
            'week': "This Week's Statistics",
            'month': "This Month's Statistics",
            'year': "This Year's Statistics",
            'all': "All Time Statistics"
        }
        self.dashboard_title.setText(titles.get(range_key, "Statistics"))
        self.update_stats()

    def on_heatmap_range_changed(self, range_key):
        """Handle time range selection change in heatmap."""
        self.update_heatmap()

    def update_stats(self):
        # Get date range from selector
        start_date, end_date = self.time_selector.get_date_range()
        
        if start_date is None:  # All time
            db_stats = self.tracker.db.get_all_time_stats()
            keys = db_stats[0] or 0
            clicks = db_stats[1] or 0
            distance = db_stats[2] or 0.0
            scroll = db_stats[3] or 0.0
        else:
            # Get stats from database for the selected range
            db_stats = self.tracker.db.get_stats_range(start_date, end_date)
            keys = db_stats[0] or 0
            clicks = db_stats[1] or 0
            distance = db_stats[2] or 0.0
            scroll = db_stats[3] or 0.0
        
        # If viewing today, also add current buffer
        if self.time_selector.current_range == 'today':
            buffer_stats = self.tracker.get_stats_snapshot()
            keys += buffer_stats.get('buffer_keys', 0)
            clicks += buffer_stats.get('buffer_clicks', 0)
            distance += buffer_stats.get('buffer_distance', 0.0)
            scroll += buffer_stats.get('buffer_scroll', 0.0)
        
        # Update Cards
        self.card_keys.update_value(f"{int(keys):,}")
        self.card_clicks.update_value(f"{int(clicks):,}")
        self.card_distance.update_value(f"{distance:.2f}")
        self.card_scroll.update_value(f"{scroll:.0f}")
        
        # Update Heatmap (only if on today or using heatmap tab)
        self.update_heatmap()

    def update_heatmap(self):
        """Update keyboard heatmap based on heatmap tab's time selector."""
        start_date, end_date = self.heatmap_time_selector.get_date_range()
        
        if start_date is None:  # All time
            # Get all heatmap data
            heatmap_data = self.tracker.db.get_heatmap_range(
                datetime.date(2000, 1, 1),
                datetime.date.today()
            )
        else:
            heatmap_data = self.tracker.db.get_heatmap_range(start_date, end_date)
        
        # Add current buffer if viewing today
        if self.heatmap_time_selector.current_range == 'today':
            buffer = self.tracker.get_stats_snapshot().get('heatmap', {})
            for key, count in buffer.items():
                heatmap_data[key] = heatmap_data.get(key, 0) + count
        
        self.heatmap_widget.update_data(heatmap_data)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

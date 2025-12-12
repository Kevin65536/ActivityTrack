"""
Screen Time Widget - Display application foreground time statistics.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QFrame, QGridLayout, QTableWidget, QTableWidgetItem,
                                QHeaderView, QComboBox, QPushButton, QButtonGroup,
                                QStackedWidget, QSplitter, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtCharts import QChart, QChartView, QPieSeries
import datetime
from ..i18n import tr


def format_duration(seconds):
    """Format seconds into human readable string (Xh Xm Xs)."""
    if seconds is None or seconds < 0:
        seconds = 0
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


class TimeRangeSelector(QWidget):
    """Button bar for selecting time range."""
    range_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_range = 'today'
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.buttons = {}
        self.range_keys = ['today', 'week', 'month', 'year', 'all']
        
        for key in self.range_keys:
            btn = QPushButton(tr(f'time.{key}'))
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, k=key: self.on_range_selected(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        
        self.buttons['today'].setChecked(True)
        layout.addStretch()
        
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
    
    def retranslate_ui(self):
        """Update button text for current language."""
        for key in self.range_keys:
            self.buttons[key].setText(tr(f'time.{key}'))
    
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
            return datetime.date(2000, 1, 1), today


class ScreenTimeCard(QFrame):
    """Card widget displaying total screen time."""
    def __init__(self, title="Total Screen Time", is_text_card=False):
        super().__init__()
        self.is_text_card = is_text_card
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 10px;
                padding: 15px;
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
        
        self.lbl_value = QLabel("0h 0m")
        if is_text_card:
            self.lbl_value.setFont(QFont("Arial", 16, QFont.Bold))
            # Enable text elision for long app names
            self.lbl_value.setWordWrap(False)
            self.lbl_value.setMaximumWidth(200)
            self.lbl_value.setToolTip("")
        else:
            self.lbl_value.setFont(QFont("Arial", 32, QFont.Bold))
        self.lbl_value.setStyleSheet("color: #00e676;")
        layout.addWidget(self.lbl_value)
    
    def update_value(self, seconds):
        self.lbl_value.setText(format_duration(seconds))
    
    def update_text(self, text):
        """Update text value with elision for long strings."""
        # Truncate long names and add ellipsis
        max_len = 20
        if len(text) > max_len:
            display_text = text[:max_len-1] + "…"
            self.lbl_value.setToolTip(text)  # Show full name on hover
        else:
            display_text = text
            self.lbl_value.setToolTip("")
        self.lbl_value.setText(display_text)


class AppTimeTable(QWidget):
    """Table showing app screen time breakdown."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            tr('screen_time.header.application'), 
            tr('screen_time.header.time'), 
            tr('screen_time.header.percentage')
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:alternate {
                background-color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #00e676;
                color: #1e1e1e;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        layout.addWidget(self.table)
        self.metadata = {}
    
    def set_metadata(self, metadata):
        """Set app metadata for friendly names."""
        self.metadata = metadata or {}
    
    def update_data(self, app_data, total_seconds):
        """
        Update table with app data.
        app_data: list of (app_name, seconds)
        total_seconds: total screen time for percentage calculation
        """
        self.table.setRowCount(len(app_data))
        
        for row, (app_name, seconds) in enumerate(app_data):
            # Get friendly name - special handling for [Idle]
            if app_name == '[Idle]':
                display_name = tr('screen_time.idle')
            elif app_name in self.metadata and self.metadata[app_name].get('friendly_name'):
                display_name = self.metadata[app_name]['friendly_name']
            else:
                display_name = app_name[:-4] if app_name.lower().endswith('.exe') else app_name
            
            # App name
            name_item = QTableWidgetItem(display_name)
            # Style idle row differently
            if app_name == '[Idle]':
                name_item.setForeground(QColor('#888888'))
            self.table.setItem(row, 0, name_item)
            
            # Time
            time_item = QTableWidgetItem(format_duration(seconds))
            time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if app_name == '[Idle]':
                time_item.setForeground(QColor('#888888'))
            self.table.setItem(row, 1, time_item)
            
            # Percentage
            pct = (seconds / total_seconds * 100) if total_seconds > 0 else 0
            pct_item = QTableWidgetItem(f"{pct:.1f}%")
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if app_name == '[Idle]':
                pct_item.setForeground(QColor('#888888'))
            self.table.setItem(row, 2, pct_item)


class AppTimePieChart(QWidget):
    """Pie chart showing app screen time distribution."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart = QChart()
        self.chart.setTitle(tr('screen_time.app_distribution'))
        self.chart.setTitleFont(QFont("Arial", 14, QFont.Bold))
        self.chart.setTitleBrush(QBrush(QColor("#ffffff")))
        self.chart.setBackgroundBrush(QBrush(QColor("#2b2b2b")))
        self.chart.legend().setLabelColor(QColor("#ffffff"))
        self.chart.legend().setAlignment(Qt.AlignRight)
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: #2b2b2b; border-radius: 10px;")
        layout.addWidget(self.chart_view)
        
        self.metadata = {}
        
        # Color palette
        self.colors = [
            "#00e676", "#2196f3", "#ff9800", "#e91e63", "#9c27b0",
            "#00bcd4", "#8bc34a", "#ffc107", "#f44336", "#673ab7",
            "#03a9f4", "#4caf50", "#ff5722", "#795548", "#607d8b"
        ]
    
    def set_metadata(self, metadata):
        self.metadata = metadata or {}
    
    def update_data(self, app_data, total_seconds):
        """
        Update pie chart with app data.
        app_data: list of (app_name, seconds), sorted by seconds desc
        """
        self.chart.removeAllSeries()
        
        series = QPieSeries()
        
        # Show top 10 apps, group rest as "Others"
        top_apps = app_data[:10]
        others_seconds = sum(s for _, s in app_data[10:]) if len(app_data) > 10 else 0
        
        for i, (app_name, seconds) in enumerate(top_apps):
            if seconds <= 0:
                continue
            
            # Get friendly name - special handling for [Idle]
            if app_name == '[Idle]':
                display_name = tr('screen_time.idle')
                slice = series.append(display_name, seconds)
                slice.setColor(QColor('#666666'))  # Gray for idle
            else:
                if app_name in self.metadata and self.metadata[app_name].get('friendly_name'):
                    display_name = self.metadata[app_name]['friendly_name']
                else:
                    display_name = app_name[:-4] if app_name.lower().endswith('.exe') else app_name
                
                slice = series.append(display_name, seconds)
                slice.setColor(QColor(self.colors[i % len(self.colors)]))
            
            slice.setLabelVisible(False)
        
        if others_seconds > 0:
            slice = series.append(tr('screen_time.others'), others_seconds)
            slice.setColor(QColor("#555555"))
            slice.setLabelVisible(False)
        
        self.chart.addSeries(series)


class ScreenTimeWidget(QWidget):
    """Main Screen Time tab widget."""
    def __init__(self, tracker, db):
        super().__init__()
        self.tracker = tracker
        self.db = db
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with title and time selector
        header = QHBoxLayout()
        
        self.title_label = QLabel(tr('screen_time.title'))
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setStyleSheet("color: white;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        self.time_selector = TimeRangeSelector()
        self.time_selector.range_changed.connect(self.on_range_changed)
        header.addWidget(self.time_selector)
        
        layout.addLayout(header)
        
        # Summary cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        self.total_time_card = ScreenTimeCard(tr('screen_time.total'))
        cards_layout.addWidget(self.total_time_card)
        
        # This card shows "Active Time" for today, or "Daily Average" for other ranges
        self.secondary_time_card = ScreenTimeCard(tr('screen_time.total_active'))
        cards_layout.addWidget(self.secondary_time_card)
        
        self.top_app_card = ScreenTimeCard(tr('screen_time.most_used'), is_text_card=True)
        cards_layout.addWidget(self.top_app_card)
        
        layout.addLayout(cards_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3d3d3d;
                width: 2px;
            }
        """)
        
        # Left: App table
        self.app_table = AppTimeTable()
        splitter.addWidget(self.app_table)
        
        # Right: Pie chart
        self.pie_chart = AppTimePieChart()
        self.pie_chart.setMinimumWidth(350)
        splitter.addWidget(self.pie_chart)
        
        splitter.setSizes([600, 350])
        
        layout.addWidget(splitter, 1)
    
    def on_range_changed(self, range_key):
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all data displays."""
        start_date, end_date = self.time_selector.get_date_range()
        is_today = self.time_selector.current_range == 'today'
        
        # Get metadata
        metadata = self.db.get_app_metadata_dict()
        self.app_table.set_metadata(metadata)
        self.pie_chart.set_metadata(metadata)
        
        # Get app foreground time from DB
        app_data = self.db.get_foreground_time_by_app(start_date, end_date)
        
        # Add buffer data if viewing today
        if is_today and self.tracker:
            buffer = self.tracker.get_foreground_time_snapshot()
            
            # Merge buffer with DB data
            app_dict = {row[0]: row[1] for row in app_data}
            for app, seconds in buffer.items():
                if app != "Unknown":
                    app_dict[app] = app_dict.get(app, 0) + seconds
            
            # Convert back to sorted list
            app_data = sorted(app_dict.items(), key=lambda x: x[1], reverse=True)
        else:
            app_data = list(app_data)
        
        # Separate idle time from active apps
        idle_seconds = 0
        active_app_data = []
        for app_name, seconds in app_data:
            if app_name == '[Idle]':
                idle_seconds = seconds
            else:
                active_app_data.append((app_name, seconds))
        
        # Calculate totals
        active_seconds = sum(s for _, s in active_app_data)
        total_seconds = active_seconds + idle_seconds
        
        # Update cards based on time range
        self.total_time_card.update_value(total_seconds)
        
        if is_today:
            # For today: show active time
            self.secondary_time_card.lbl_title.setText(tr('screen_time.total_active'))
            self.secondary_time_card.update_value(active_seconds)
        else:
            # For week/month/year/all: show daily average
            self.secondary_time_card.lbl_title.setText(tr('screen_time.daily_avg'))
            if start_date and end_date:
                days = (end_date - start_date).days + 1
            else:
                days = 1
            avg_seconds = total_seconds / days if days > 0 else 0
            self.secondary_time_card.update_value(avg_seconds)
        
        # Find top app (excluding idle)
        if active_app_data:
            top_app_name = active_app_data[0][0]
            if top_app_name in metadata and metadata[top_app_name].get('friendly_name'):
                top_display = metadata[top_app_name]['friendly_name']
            else:
                top_display = top_app_name[:-4] if top_app_name.lower().endswith('.exe') else top_app_name
            self.top_app_card.update_text(top_display)
        else:
            self.top_app_card.update_text(tr('screen_time.no_data'))
        
        # Include idle in display data (at the end)
        display_data = active_app_data.copy()
        if idle_seconds > 0:
            display_data.append(('[Idle]', idle_seconds))
        
        # Update table and pie chart with all data including idle
        self.app_table.update_data(display_data, total_seconds)
        self.pie_chart.update_data(display_data, total_seconds)

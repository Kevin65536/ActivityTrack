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
    """Button bar for selecting time range: Today, Yesterday, Week, Month, Year/All"""
    range_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_range = 'today'
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.buttons = {}
        # Regular button keys (Yesterday added, Year/All moved to dropdown)
        self.button_keys = ['today', 'yesterday', 'week', 'month']
        # Dropdown keys for less common options
        self.dropdown_keys = ['year', 'all']
        
        # Create regular buttons
        for key in self.button_keys:
            btn = QPushButton(tr(f'time.{key}'))
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, k=key: self.on_range_selected(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        
        # Create dropdown for Year/All Time
        self.extended_combo = QComboBox()
        self.extended_combo.setMinimumWidth(100)
        for key in self.dropdown_keys:
            self.extended_combo.addItem(tr(f'time.{key}'), key)
        self.extended_combo.currentIndexChanged.connect(self.on_combo_selected)
        layout.addWidget(self.extended_combo)
        
        # Style the combo to look like other buttons when not active
        self._combo_active = False
        self._update_combo_style()
        
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
    
    def _update_combo_style(self):
        """Update combo box style based on whether it's the active selection."""
        if self._combo_active:
            self.extended_combo.setStyleSheet("""
                QComboBox {
                    background-color: #00e676;
                    color: #1e1e1e;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #1e1e1e;
                    margin-right: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    selection-background-color: #00e676;
                    selection-color: #1e1e1e;
                    border: 1px solid #3d3d3d;
                }
            """)
        else:
            self.extended_combo.setStyleSheet("""
                QComboBox {
                    background-color: #3d3d3d;
                    color: #aaaaaa;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    background-color: #4a4a4a;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #aaaaaa;
                    margin-right: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    selection-background-color: #00e676;
                    selection-color: #1e1e1e;
                    border: 1px solid #3d3d3d;
                }
            """)
    
    def retranslate_ui(self):
        """Update button/combo text for current language."""
        for key in self.button_keys:
            self.buttons[key].setText(tr(f'time.{key}'))
        # Update combo items
        for i, key in enumerate(self.dropdown_keys):
            self.extended_combo.setItemText(i, tr(f'time.{key}'))
    
    def on_range_selected(self, key):
        """Handle button selection."""
        # Uncheck all buttons
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)
        # Deactivate combo style
        self._combo_active = False
        self._update_combo_style()
        
        self.current_range = key
        self.range_changed.emit(key)
    
    def on_combo_selected(self, index):
        """Handle combo box selection."""
        key = self.extended_combo.itemData(index)
        if key:
            # Uncheck all buttons
            for btn in self.buttons.values():
                btn.setChecked(False)
            # Activate combo style
            self._combo_active = True
            self._update_combo_style()
            
            self.current_range = key
            self.range_changed.emit(key)
    
    def get_date_range(self):
        """Returns (start_date, end_date) based on current selection."""
        today = datetime.date.today()
        if self.current_range == 'today':
            return today, today
        elif self.current_range == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            return yesterday, yesterday
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
    """Pie chart showing app screen time distribution. Click to toggle idle time."""
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
        
        # Disable animations to prevent flickering
        self.chart.setAnimationOptions(QChart.NoAnimation)
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: #2b2b2b; border-radius: 10px;")
        layout.addWidget(self.chart_view)
        
        self.metadata = {}
        
        # State for idle toggle
        self.show_idle = True  # Default: show idle time
        self._cached_app_data = []
        self._cached_total_seconds = 0
        
        # Persistent series - reuse instead of recreating
        self._series = QPieSeries()
        self.chart.addSeries(self._series)
        
        # Color palette
        self.colors = [
            "#00e676", "#2196f3", "#ff9800", "#e91e63", "#9c27b0",
            "#00bcd4", "#8bc34a", "#ffc107", "#f44336", "#673ab7",
            "#03a9f4", "#4caf50", "#ff5722", "#795548", "#607d8b"
        ]
        
        # Enable mouse tracking and click detection
        self.chart_view.setMouseTracking(True)
        self.chart_view.setCursor(Qt.PointingHandCursor)
        self.chart_view.mousePressEvent = self._on_chart_clicked
    
    def _on_chart_clicked(self, event):
        """Handle click on the chart to toggle idle time display."""
        self.show_idle = not self.show_idle
        self._redraw_chart()
    
    def set_metadata(self, metadata):
        self.metadata = metadata or {}
    
    def update_data(self, app_data, total_seconds):
        """
        Update pie chart with app data.
        app_data: list of (app_name, seconds), sorted by seconds desc
        """
        # Cache the data for toggle functionality
        self._cached_app_data = list(app_data)
        self._cached_total_seconds = total_seconds
        self._redraw_chart()
    
    def _redraw_chart(self):
        """Redraw the chart based on current show_idle state."""
        # Filter data based on show_idle state
        if self.show_idle:
            app_data = self._cached_app_data
            total_seconds = self._cached_total_seconds
        else:
            # Exclude idle time
            app_data = [(app, secs) for app, secs in self._cached_app_data if app != '[Idle]']
            total_seconds = sum(secs for _, secs in app_data)
        
        # Prepare new slice data
        slice_data = []  # List of (display_name, seconds, color)
        
        if app_data and total_seconds > 0:
            # Show top 10 apps, group rest as "Others"
            top_apps = app_data[:10]
            others_seconds = sum(s for _, s in app_data[10:]) if len(app_data) > 10 else 0
            
            color_index = 0
            for app_name, seconds in top_apps:
                if seconds <= 0:
                    continue
                
                # Get friendly name - special handling for [Idle]
                if app_name == '[Idle]':
                    display_name = tr('screen_time.idle')
                    color = QColor('#666666')  # Gray for idle
                else:
                    if app_name in self.metadata and self.metadata[app_name].get('friendly_name'):
                        display_name = self.metadata[app_name]['friendly_name']
                    else:
                        display_name = app_name[:-4] if app_name.lower().endswith('.exe') else app_name
                    color = QColor(self.colors[color_index % len(self.colors)])
                    color_index += 1
                
                slice_data.append((display_name, seconds, color))
            
            if others_seconds > 0:
                slice_data.append((tr('screen_time.others'), others_seconds, QColor("#555555")))
        
        # Update slices in-place to avoid flickering
        current_count = self._series.count()
        new_count = len(slice_data)
        
        # Update existing slices or add new ones
        for i, (display_name, seconds, color) in enumerate(slice_data):
            if i < current_count:
                # Update existing slice
                pie_slice = self._series.slices()[i]
                pie_slice.setLabel(display_name)
                pie_slice.setValue(seconds)
                pie_slice.setColor(color)
                pie_slice.setLabelVisible(False)
            else:
                # Add new slice
                pie_slice = self._series.append(display_name, seconds)
                pie_slice.setColor(color)
                pie_slice.setLabelVisible(False)
        
        # Remove extra slices (from end to start to avoid index shifting)
        while self._series.count() > new_count:
            pie_slice = self._series.slices()[-1]
            self._series.remove(pie_slice)


class ScreenTimeWidget(QWidget):
    """Main Screen Time tab widget."""
    def __init__(self, tracker, db, config=None):
        super().__init__()
        self.tracker = tracker
        self.db = db
        self.config = config
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with title, category filter, and time selector
        header = QHBoxLayout()
        
        self.title_label = QLabel(tr('screen_time.title'))
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setStyleSheet("color: white;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        # Category filter dropdown
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(120)
        self.category_filter.addItem(tr('category.all'), 'all')
        self.category_filter.addItem(tr('category.productivity'), 'productivity')
        self.category_filter.addItem(tr('category.other'), 'other')
        self.category_filter.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox:hover {
                background-color: #3d3d3d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #aaaaaa;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #00e676;
                selection-color: #1e1e1e;
                border: 1px solid #3d3d3d;
            }
        """)
        self.category_filter.currentIndexChanged.connect(self.on_category_changed)
        header.addWidget(self.category_filter)
        
        header.addSpacing(10)
        
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
    
    def on_category_changed(self, index):
        """Handle category filter selection change."""
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all data displays."""
        start_date, end_date = self.time_selector.get_date_range()
        is_today = self.time_selector.current_range == 'today'
        is_single_day = self.time_selector.current_range in ('today', 'yesterday')
        
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
        
        # Apply category filter
        selected_category = self.category_filter.currentData()
        if selected_category and selected_category != 'all' and self.config:
            # Get app groups from config
            app_groups = self.config.app_groups
            category_apps = set(app_groups.get(selected_category, []))
            
            # Filter app_data to only include apps in the selected category
            # Also exclude [Idle] when category filter is active
            app_data = [(app, secs) for app, secs in app_data 
                       if app in category_apps]
        
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

        # Guard rails: a single day's total cannot exceed the time available.
        # This also protects the UI from already-polluted DB data.
        if is_single_day:
            if is_today:
                now = datetime.datetime.now()
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                max_total = max(0, int((now - midnight).total_seconds()))
            else:
                max_total = 24 * 3600

            if total_seconds > max_total and total_seconds > 0:
                scale = max_total / total_seconds
                active_seconds *= scale
                idle_seconds *= scale
                total_seconds = max_total
                active_app_data = [(app, seconds * scale) for app, seconds in active_app_data]
        
        # Update cards based on time range
        self.total_time_card.update_value(total_seconds)
        
        if is_single_day:
            # For today/yesterday: show active time
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

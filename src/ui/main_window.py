from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QTabWidget, QFrame, QGridLayout, QPushButton,
                                QButtonGroup, QSizePolicy, QStackedWidget, QComboBox,
                                QSplitter)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from .utils import HeatmapWidget, MouseHeatmapWidget
from .history_chart import HistoryChartWidget
from .app_stats_widget import AppStatsWidget
from .pie_chart import AppPieChartWidget
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
        self.resize(1200, 800)
        
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
        
        # Applications Tab
        self.apps_tab = QWidget()
        self.setup_apps()
        self.tabs.addTab(self.apps_tab, "Applications")
        
        # History Tab
        self.history_tab = QWidget()
        self.setup_history()
        self.tabs.addTab(self.history_tab, "History")

        # Hook after all tabs are created
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Timer to update UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000) # Update every second
        
        # Initial update
        self.update_stats()

    def on_tab_changed(self, index):
        try:
            title = self.tabs.tabText(index)
        except Exception:
            title = str(index)
        print(f"[DEBUG] Tab changed to {index} ({title})")
        # Immediately refresh apps tab when selected
        if self.tabs.widget(index) == self.apps_tab:
            try:
                self.update_apps()
            except Exception as e:
                print(f"[ERROR] update_apps on tab change failed: {e}")
                import traceback
                traceback.print_exc()

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
        
        # Header with controls (no title to save horizontal space)
        header = QHBoxLayout()
        
        # View Switcher (Keyboard / Mouse) - placed at left
        self.view_switcher_layout = QHBoxLayout()
        self.view_switcher_layout.setSpacing(0)
        
        self.btn_keyboard = QPushButton("Keyboard")
        self.btn_keyboard.setCheckable(True)
        self.btn_keyboard.setChecked(True)
        self.btn_mouse = QPushButton("Mouse")
        self.btn_mouse.setCheckable(True)
        
        # Determine strict fixed size to ensure consistency
        self.btn_keyboard.setFixedSize(100, 32)
        self.btn_mouse.setFixedSize(100, 32)
        
        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.btn_keyboard, 0)
        self.view_group.addButton(self.btn_mouse, 1)
        self.view_group.idClicked.connect(self.on_heatmap_type_changed)
        
        self.view_switcher_layout.addWidget(self.btn_keyboard)
        self.view_switcher_layout.addWidget(self.btn_mouse)
        
        header.addLayout(self.view_switcher_layout)
        header.addStretch()
        
        # Style for the toggle buttons
        switcher_style = """
            QPushButton {
                background-color: #2b2b2b;
                color: #aaaaaa;
                border: 1px solid #3d3d3d;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:checked {
                background-color: #00e676;
                color: #1e1e1e;
                border: 1px solid #00e676;
            }
            QPushButton:first {
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-right: none;
            }
            QPushButton:last {
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                border-left: none;
            }
        """
        self.btn_keyboard.setStyleSheet(switcher_style)
        self.btn_mouse.setStyleSheet(switcher_style)
        
        # App Filter Dropdown
        self.heatmap_app_filter = QComboBox()
        self.heatmap_app_filter.setMinimumWidth(180)
        self.heatmap_app_filter.setStyleSheet("""
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
        self.heatmap_app_filter.addItem("All Applications")
        self.heatmap_app_filter.currentTextChanged.connect(self.on_heatmap_app_changed)
        header.addWidget(self.heatmap_app_filter)
        
        header.addSpacing(10)
        
        self.heatmap_time_selector = TimeRangeSelector()
        self.heatmap_time_selector.range_changed.connect(self.on_heatmap_range_changed)
        header.addWidget(self.heatmap_time_selector)
        
        layout.addLayout(header)
        
        # Stacked Widget for Heatmaps
        self.heatmap_stack = QStackedWidget()
        
        self.keyboard_heatmap = HeatmapWidget()
        self.mouse_heatmap = MouseHeatmapWidget()
        
        self.heatmap_stack.addWidget(self.keyboard_heatmap)
        self.heatmap_stack.addWidget(self.mouse_heatmap)
        
        layout.addWidget(self.heatmap_stack)
        
        # Refresh app list
        self.refresh_heatmap_app_list()
        layout.addStretch()

    def on_heatmap_type_changed(self, index):
        self.heatmap_stack.setCurrentIndex(index)
        self.update_heatmap()

    def setup_apps(self):
        print("[DEBUG] setup_apps: Starting...")
        try:
            layout = QVBoxLayout(self.apps_tab)
            layout.setSpacing(20)
            layout.setContentsMargins(30, 30, 30, 30)
            
            # Header: Chart/Table (left), Metric dropdown (left), Time selector (right)
            header = QHBoxLayout()
            header.setSpacing(10)

            # View toggle (Chart/Table) - leftmost
            self.apps_view_group = QButtonGroup(self)
            self.btn_apps_chart = QPushButton("Chart")
            self.btn_apps_chart.setCheckable(True)
            self.btn_apps_chart.setChecked(True)
            self.btn_apps_chart.setFixedSize(80, 32)
            self.btn_apps_table = QPushButton("Table")
            self.btn_apps_table.setCheckable(True)
            self.btn_apps_table.setFixedSize(80, 32)
            self.apps_view_group.addButton(self.btn_apps_chart, 0)
            self.apps_view_group.addButton(self.btn_apps_table, 1)
            self.apps_view_group.idClicked.connect(self.on_apps_view_changed)
            header.addWidget(self.btn_apps_chart)
            header.addWidget(self.btn_apps_table)
            
            header.addSpacing(10)
            
            # Metric selector as dropdown (visible always, disabled in Table view)
            self.apps_metric_combo = QComboBox()
            self.apps_metric_combo.setFixedWidth(120)
            self.apps_metric_combo.addItems(["Keys", "Clicks", "Scrolls", "Distance"])
            self.apps_metric_combo.currentIndexChanged.connect(self.on_apps_metric_changed)
            self.apps_metric_combo.setStyleSheet("""
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
                QComboBox:disabled {
                    background-color: #1e1e1e;
                    color: #666666;
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
                QComboBox::down-arrow:disabled {
                    border-top-color: #444444;
                }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    selection-background-color: #00e676;
                    selection-color: #1e1e1e;
                    border: 1px solid #3d3d3d;
                }
            """)
            header.addWidget(self.apps_metric_combo)
            self.apps_metric_keys = ['keys', 'clicks', 'scrolls', 'distance']
            
            header.addStretch()
            
            # Time selector
            self.apps_time_selector = TimeRangeSelector()
            self.apps_time_selector.range_changed.connect(self.on_apps_range_changed)
            header.addWidget(self.apps_time_selector)
            
            # Apply unified button style
            unified_style = """
                QPushButton {
                    background-color: #2b2b2b;
                    color: #aaaaaa;
                    border: 1px solid #3d3d3d;
                    border-radius: 5px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QPushButton:checked {
                    background-color: #00e676;
                    color: #1e1e1e;
                    border: 1px solid #00e676;
                    font-weight: bold;
                }
            """
            for btn in self.apps_view_group.buttons():
                btn.setStyleSheet(unified_style)
            
            layout.addLayout(header)
            print("[DEBUG] setup_apps: Header created")
            
            # Content: stacked views (Chart or Table)
            self.apps_stack = QStackedWidget()

            self.app_pie_chart = AppPieChartWidget()
            self.app_pie_chart.setMinimumHeight(480)
            self.apps_stack.addWidget(self.app_pie_chart)

            self.app_stats_widget = AppStatsWidget()
            self.apps_stack.addWidget(self.app_stats_widget)

            layout.addWidget(self.apps_stack, 1)
            print("[DEBUG] setup_apps: Completed successfully")
        except Exception as e:
            print(f"[ERROR] setup_apps failed: {e}")
            import traceback
            traceback.print_exc()

    def on_apps_range_changed(self, range_key):
        self.update_apps()

    def on_apps_view_changed(self, idx):
        self.apps_stack.setCurrentIndex(idx)
        # Enable/disable metric dropdown: enabled only in Chart view (idx=0)
        self.apps_metric_combo.setEnabled(idx == 0)
    
    def on_apps_metric_changed(self, idx):
        metric = self.apps_metric_keys[idx]
        self.app_pie_chart.set_metric(metric)
        # Refresh chart with new metric
        self.app_pie_chart.refresh_display()

    def update_apps(self):
        print("[DEBUG] update_apps: Starting...")
        try:
            start_date, end_date = self.apps_time_selector.get_date_range()
            print(f"[DEBUG] update_apps: date range = {start_date} to {end_date}")
            
            # Fetch from DB
            stats = self.tracker.db.get_app_stats_summary(limit=100, start_date=start_date, end_date=end_date)
            print(f"[DEBUG] update_apps: got {len(stats) if stats else 0} stats from DB")
            
            # Convert to list of tuples if not already (fetchall returns list of tuples)
            # Stats are (app_name, keys, clicks, scrolls, distance)
            # We need to sanitize None values from SQL SUMs
            
            clean_stats = []
            for row in stats:
                clean_stats.append((
                    row[0],             # name
                    row[1] or 0,        # keys
                    row[2] or 0,        # clicks
                    row[3] or 0,        # scrolls
                    row[4] or 0.0       # distance
                ))
                
            # Add buffer ONLY if 'today' is selected
            if self.apps_time_selector.current_range == 'today':
                buffer = self.tracker.app_stats_buffer # direct access or via snapshot?
                # Prefer snapshot to be thread safe, but get_stats_snapshot doesn't return detailed app stats currently
                # Let's add app_stats to get_stats_snapshot or access via lock.
                # Accessing via lock is safer.
                with self.tracker.lock:
                    buffer_snapshot = dict(self.tracker.app_stats_buffer) # Copy it
                
                # Merge logic... this is tricky with list of tuples.
                # Convert DB stats to dict for merging
                stats_dict = {row[0]: list(row[1:]) for row in clean_stats}
                
                for app, data in buffer_snapshot.items():
                    if app not in stats_dict:
                        stats_dict[app] = [0, 0, 0, 0.0]
                    
                    stats_dict[app][0] += data.get('keys', 0)
                    stats_dict[app][1] += data.get('clicks', 0)
                    stats_dict[app][2] += data.get('scrolls', 0)
                    stats_dict[app][3] += data.get('distance', 0.0)
                    
                # Convert back to list
                clean_stats = [(app, *vals) for app, vals in stats_dict.items()]
                # Sort by keys (default)
                clean_stats.sort(key=lambda x: x[1], reverse=True)
                
            # PROPOSED: Fetch Metadata
            print("[DEBUG] update_apps: Fetching metadata...")
            metadata = self.tracker.db.get_app_metadata_dict()
            print(f"[DEBUG] update_apps: got {len(metadata) if metadata else 0} metadata entries")
            
            print("[DEBUG] update_apps: Updating table...")
            self.app_stats_widget.update_data(clean_stats, metadata)
            print("[DEBUG] update_apps: Updating pie chart...")
            self.app_pie_chart.update_data(clean_stats, metadata)
            print("[DEBUG] update_apps: Completed successfully")
        except Exception as e:
            print(f"[ERROR] update_apps failed: {e}")
            import traceback
            traceback.print_exc()


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

    def on_heatmap_app_changed(self, app_name):
        """Handle app filter selection change in heatmap."""
        self.update_heatmap()

    def refresh_heatmap_app_list(self):
        """Refresh the app list in heatmap filter dropdown."""
        current_text = self.heatmap_app_filter.currentText()
        self.heatmap_app_filter.blockSignals(True)
        self.heatmap_app_filter.clear()
        self.heatmap_app_filter.addItem("All Applications")
        
        # Get all apps from database
        apps = self.tracker.db.get_all_apps()
        metadata = self.tracker.db.get_app_metadata_dict()
        
        for app in apps:
            # Use friendly name if available, otherwise strip .exe
            if app in metadata and metadata[app].get('friendly_name'):
                display_name = metadata[app]['friendly_name']
            else:
                # Strip .exe suffix for cleaner display
                display_name = app[:-4] if app.lower().endswith('.exe') else app
            self.heatmap_app_filter.addItem(display_name, app)  # userData is the raw app_name
        
        # Restore previous selection if still exists
        idx = self.heatmap_app_filter.findText(current_text)
        if idx >= 0:
            self.heatmap_app_filter.setCurrentIndex(idx)
        
        self.heatmap_app_filter.blockSignals(False)

    def get_selected_heatmap_app(self):
        """Get the raw app_name from the heatmap filter dropdown."""
        idx = self.heatmap_app_filter.currentIndex()
        if idx == 0:
            return None  # "All Applications"
        # Get userData (raw app_name)
        return self.heatmap_app_filter.itemData(idx)

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
        
        # Refresh app list periodically (every 10 updates = 10 seconds)
        if not hasattr(self, '_app_list_refresh_counter'):
            self._app_list_refresh_counter = 0
        self._app_list_refresh_counter += 1
        if self._app_list_refresh_counter >= 10:
            self._app_list_refresh_counter = 0
            self.refresh_heatmap_app_list()
        
        # Update Heatmap (only if on today or using heatmap tab)
        self.update_heatmap()
        
        # Update Apps (only if visible or on today)
        if self.tabs.currentWidget() == self.apps_tab:
            self.update_apps()

    def update_heatmap(self):
        """Update keyboard heatmap based on heatmap tab's time selector and app filter."""
        start_date, end_date = self.heatmap_time_selector.get_date_range()
        app_filter = self.get_selected_heatmap_app()
        
        if self.view_group.checkedId() == 0:
            # Keyboard Heatmap
            if start_date is None:  # All time
                heatmap_data = self.tracker.db.get_heatmap_range(
                    datetime.date(2000, 1, 1),
                    datetime.date.today(),
                    app_filter=app_filter
                )
            else:
                heatmap_data = self.tracker.db.get_heatmap_range(start_date, end_date, app_filter=app_filter)
            
            # Add current buffer if viewing today
            if self.heatmap_time_selector.current_range == 'today':
                snapshot = self.tracker.get_stats_snapshot()
                if app_filter:
                    # Get app-specific buffer
                    app_buffer = snapshot.get('app_heatmap_buffer', {}).get(app_filter, {})
                    for key, count in app_buffer.items():
                        heatmap_data[key] = heatmap_data.get(key, 0) + count
                else:
                    # Get global buffer
                    buffer = snapshot.get('heatmap', {})
                    for key, count in buffer.items():
                        heatmap_data[key] = heatmap_data.get(key, 0) + count
            
            self.keyboard_heatmap.update_data(heatmap_data)
            
        else:
            # Mouse Heatmap
            if start_date is None:
                raw_data = self.tracker.db.get_mouse_heatmap_range(
                    datetime.date(2000, 1, 1),
                    datetime.date.today(),
                    app_filter=app_filter
                )
            else:
                raw_data = self.tracker.db.get_mouse_heatmap_range(start_date, end_date, app_filter=app_filter)
                
            # raw_data is list of (x, y, count) tuples
            # Convert to dict for widget
            mouse_data = {(row[0], row[1]): row[2] for row in raw_data}
            
            # Add buffer if today
            if self.heatmap_time_selector.current_range == 'today':
                snapshot = self.tracker.get_stats_snapshot()
                if app_filter:
                    # Get app-specific buffer
                    app_buffer = snapshot.get('app_mouse_heatmap_buffer', {}).get(app_filter, {})
                    for (x, y), count in app_buffer.items():
                        mouse_data[(x, y)] = mouse_data.get((x, y), 0) + count
                else:
                    # Get global buffer
                    buffer = snapshot.get('mouse_heatmap', {})
                    for (x, y), count in buffer.items():
                        mouse_data[(x, y)] = mouse_data.get((x, y), 0) + count
            
            self.mouse_heatmap.update_data(mouse_data)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

"""
History Chart Widget - Displays detailed analytics with app filtering
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QComboBox, QFrame, QStackedWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import font_manager
import matplotlib.pyplot as plt
import datetime
from ..i18n import tr, tr_list, get_language

# Common Styles
BTN_STYLE_BAR = """
    QPushButton {
        background-color: #3d3d3d;
        color: #aaaaaa;
        border: none;
        border-radius: 5px;
        padding: 6px 12px;
        font-size: 12px;
    }
    QPushButton:hover { background-color: #4a4a4a; }
    QPushButton:checked {
        background-color: #00e676;
        color: #1e1e1e;
        font-weight: bold;
    }
"""

BTN_STYLE_TAB = """
    QPushButton {
        background-color: transparent;
        color: #aaaaaa;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton:hover { color: #ffffff; }
    QPushButton:checked {
        color: #00e676;
        border-bottom: 2px solid #00e676;
    }
"""

COMBO_STYLE = """
    QComboBox {
        background-color: #3d3d3d;
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 5px;
        padding: 5px 10px;
        min-width: 200px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 15px;
        border-left-width: 1px;
        border-left-color: darkgray;
        border-left-style: solid;
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }
    QComboBox:on { background-color: #4a4a4a; }
    QListView {
        background-color: #3d3d3d;
        color: #ffffff;
        selection-background-color: #00e676;
        selection-color: #1e1e1e;
    }
"""

_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "PingFang SC",
    "WenQuanYi Micro Hei"
]

_FONT_INITIALIZED = False


class BaseChartWidget(QWidget):
    """Base widget for shared chart functionality."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        # Header for controls
        self.header = QHBoxLayout()
        self.layout.addLayout(self.header)
        
        # Chart
        plt.style.use('dark_background')
        self._ensure_font_support()
        # Taller figure since we only have one chart now
        self.figure = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #1e1e1e;")
        self.layout.addWidget(self.canvas)
        
    def setup_buttons(self, button_map):
        """Helper to create toggle buttons."""
        self.btn_group = {}
        for key, label in button_map:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(BTN_STYLE_BAR)
            btn.clicked.connect(lambda c, k=key: self.on_mode_changed(k))
            self.header.addWidget(btn)
            self.btn_group[key] = btn
        self.header.addStretch() # Push buttons to left
            
    def set_active_button(self, key):
        for k, btn in self.btn_group.items():
            btn.setChecked(k == key)

    def on_mode_changed(self, key):
        raise NotImplementedError
    
    def set_common_style(self, ax, title_text):
        ax.set_title(title_text, color='#dddddd', pad=20)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#3d3d3d')
        ax.spines['left'].set_color('#3d3d3d')
        ax.tick_params(colors='#aaaaaa')
        ax.grid(True, alpha=0.1)
        ax.set_ylim(bottom=0) # Non-negative axis

    def _ensure_font_support(self):
        """Configure matplotlib fonts so Chinese labels render correctly."""
        global _FONT_INITIALIZED
        if _FONT_INITIALIZED:
            return
        _FONT_INITIALIZED = True

        if get_language() != 'zh':
            return

        installed = {f.name for f in font_manager.fontManager.ttflist}
        for font_name in _CJK_FONT_CANDIDATES:
            if font_name in installed:
                plt.rcParams['font.family'] = font_name
                plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                break

class TimelineWidget(BaseChartWidget):
    """Displays user activity over time (Today/Week/History)."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_app = None
        self.current_mode = 'today'
        
        # Buttons
        self.setup_buttons([
            ('today', tr('time.today')),
            ('week', tr('time.week')),
            ('month', tr('time.month')),
            ('year', tr('time.year'))
        ])
        self.set_active_button('today')
        
    def on_mode_changed(self, key):
        self.current_mode = key
        self.set_active_button(key)
        self.refresh()
        
    def update_filter(self, app_name):
        self.current_app = app_name
        self.refresh()
        
    def refresh(self):
        self.figure.clear()
        
        try:
            if self.current_mode == 'today':
                self.plot_today()
            else:
                self.plot_history()
        except Exception as e:
            print(f"Chart Error: {e}")
            
        self.canvas.draw()
        
    def plot_today(self):
        ax = self.figure.add_subplot(111)
        data = self.db.get_today_hourly_stats(self.current_app)
        # data: list of (hour, keys, clicks)
        
        # Fill all 24 hours
        hours = list(range(24))
        keys_map = {r[0]: r[1] or 0 for r in data}
        clicks_map = {r[0]: r[2] or 0 for r in data}
        
        keys = [keys_map.get(h, 0) for h in hours]
        clicks = [clicks_map.get(h, 0) for h in hours]
        
        # Plot keys as bars
        ax.bar(hours, keys, color='#00e676', alpha=0.7, label=tr('history.legend.keys'))
        
        ax.plot(hours, clicks, 'o-', color='#2196f3', linewidth=2, label=tr('history.legend.clicks'))
        
        self.set_common_style(ax, tr('history.chart.today'))
        ax.set_xlabel("Hour")
        ax.set_ylabel("Count")
        ax.legend()
        ax.set_xticks(hours[::2])
        
    def plot_history(self):
        today = datetime.date.today()
        start_date = today
        
        if self.current_mode == 'week':
            start_date = today - datetime.timedelta(days=6)
        elif self.current_mode == 'month':
            start_date = today - datetime.timedelta(days=29)
        elif self.current_mode == 'year':
            start_date = today - datetime.timedelta(days=364)
            
        raw_data = self.db.get_daily_history(start_date, today, self.current_app)
        
        if not raw_data:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, tr('history.no_data'), ha='center', color='gray')
            ax.set_facecolor('#1e1e1e')
            return

        dates = [r[0] for r in raw_data]
        if isinstance(dates[0], str):
            dates = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
            
        keys = [r[1] or 0 for r in raw_data]
        clicks = [r[2] or 0 for r in raw_data]
        
        ax = self.figure.add_subplot(111)
        # Plot keys as bars (convert dates to numbers for bar width logic if needed, but matplotlib handles dates well)
        # We might need to adjust width if it's too thin/thick. Auto usually works okay for simple time series.
        # Let's try standard bar first.
        ax.bar(dates, keys, color='#00e676', alpha=0.7, label=tr('history.legend.keys'))
        
        ax.plot(dates, clicks, 'o-', color='#2196f3', linewidth=2, label=tr('history.legend.clicks'))
        
        self.set_common_style(ax, tr('history.chart.history'))
        ax.legend()
        self.figure.autofmt_xdate()

class InsightWidget(BaseChartWidget):
    """Displays average statistics (Day of Week / Hour of Day) and Top Apps."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_app = None
        self.current_mode = 'weekday'
        self.top_apps_submode = 'weekday'  # Sub-mode for Top Apps (weekday or hourly)
        
        self.setup_buttons([
            ('weekday', tr('history.weekday')),
            ('hour', tr('history.hourly')),
            ('top_apps', tr('history.top_apps'))
        ])
        self.set_active_button('weekday')
        
        # Add secondary toggle row for Top Apps sub-mode
        self.sub_toggle_frame = QFrame()
        self.sub_toggle_layout = QHBoxLayout(self.sub_toggle_frame)
        self.sub_toggle_layout.setContentsMargins(0, 5, 0, 0)
        self.sub_toggle_layout.setSpacing(5)
        
        self.btn_top_weekday = QPushButton(tr('history.weekday'))
        self.btn_top_weekday.setCheckable(True)
        self.btn_top_weekday.setChecked(True)
        self.btn_top_weekday.setStyleSheet(BTN_STYLE_BAR)
        self.btn_top_weekday.clicked.connect(lambda: self.set_top_apps_submode('weekday'))
        
        self.btn_top_hourly = QPushButton(tr('history.hourly'))
        self.btn_top_hourly.setCheckable(True)
        self.btn_top_hourly.setStyleSheet(BTN_STYLE_BAR)
        self.btn_top_hourly.clicked.connect(lambda: self.set_top_apps_submode('hourly'))
        
        self.sub_toggle_layout.addWidget(self.btn_top_weekday)
        self.sub_toggle_layout.addWidget(self.btn_top_hourly)
        self.sub_toggle_layout.addStretch()
        
        # Insert sub-toggle after header
        self.layout.insertWidget(1, self.sub_toggle_frame)
        self.sub_toggle_frame.hide()  # Hidden by default
        
    def set_top_apps_submode(self, mode):
        self.top_apps_submode = mode
        self.btn_top_weekday.setChecked(mode == 'weekday')
        self.btn_top_hourly.setChecked(mode == 'hourly')
        self.refresh()
        
    def on_mode_changed(self, key):
        self.current_mode = key
        self.set_active_button(key)
        # Show/hide sub-toggle based on mode
        self.sub_toggle_frame.setVisible(key == 'top_apps')
        self.refresh()
        
    def update_filter(self, app_name):
        self.current_app = app_name
        self.refresh()
        
    def refresh(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if self.current_mode == 'weekday':
            self.plot_weekday(ax)
        elif self.current_mode == 'hour':
            self.plot_hourly(ax)
        elif self.current_mode == 'top_apps':
            if self.top_apps_submode == 'weekday':
                self.plot_top_apps_weekday(ax)
            else:
                self.plot_top_apps_hourly(ax)
            
        self.canvas.draw()
        
    def plot_weekday(self, ax):
        data = self.db.get_day_of_week_averages(self.current_app)
        days_map = {int(r[0]): r for r in data}
        
        ordered_indices = [1, 2, 3, 4, 5, 6, 0]
        labels = tr_list('history.weekdays')
        
        avg_keys = []
        avg_clicks = []
        
        for idx in ordered_indices:
            row = days_map.get(idx)
            if row:
                avg_keys.append(row[1] or 0)
                avg_clicks.append(row[2] or 0)
            else:
                avg_keys.append(0)
                avg_clicks.append(0)
                
        import numpy as np
        x = np.arange(len(labels))
        
        # Plot keys as bars
        ax.bar(x, avg_keys, color='#00e676', alpha=0.7, label=tr('history.legend.avg_keys'))
        
        # Plot clicks as line
        ax.plot(x, avg_clicks, 'o-', color='#2196f3', linewidth=2, label=tr('history.legend.avg_clicks'))
        
        self.set_common_style(ax, tr('history.chart.weekday'))
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()

    def plot_hourly(self, ax):
        data = self.db.get_hour_of_day_averages(self.current_app)
        hours = list(range(24))
        data_map = {r[0]: r for r in data}
        
        avg_keys = [data_map[h][1] if h in data_map else 0 for h in hours]
        avg_clicks = [data_map[h][2] if h in data_map else 0 for h in hours]
        
        # Plot keys as bars
        ax.bar(hours, avg_keys, color='#00e676', alpha=0.7, label=tr('history.legend.avg_keys'))
        
        # Plot clicks as line
        ax.plot(hours, avg_clicks, 'o-', color='#2196f3', linewidth=2, label=tr('history.legend.avg_clicks'))
        
        self.set_common_style(ax, tr('history.chart.hourly'))
        ax.set_xticks(hours[::2])
        ax.legend()

    def plot_top_apps_weekday(self, ax):
        """Plot most used app for each weekday."""
        import numpy as np
        
        data = self.db.get_top_app_by_weekday()
        labels = tr_list('history.weekdays')
        
        if not data:
            ax.text(0.5, 0.5, tr('history.no_data'), ha='center', va='center', 
                    color='gray', fontsize=14, transform=ax.transAxes)
            ax.set_facecolor('#1e1e1e')
            return
        
        # Get metadata for friendly names
        metadata = self.db.get_app_metadata_dict()
        
        # Build data for all 7 days (Mon=0 to Sun=6)
        data_map = {r[0]: r for r in data}  # weekday_idx -> (idx, app_name, activity)
        
        # Collect unique apps to assign colors
        unique_apps = list(set(r[1] for r in data))
        color_palette = ['#00e676', '#2196f3', '#ff9800', '#e91e63', '#9c27b0', '#00bcd4', '#ffeb3b']
        app_colors = {app: color_palette[i % len(color_palette)] for i, app in enumerate(unique_apps)}
        
        x = np.arange(len(labels))
        activities = []
        bar_colors = []
        app_labels = []
        
        for idx in range(7):
            if idx in data_map:
                _, app_name, activity = data_map[idx]
                activities.append(activity or 0)
                bar_colors.append(app_colors[app_name])
                # Get friendly name if available
                friendly = metadata.get(app_name, {}).get('friendly_name') or app_name
                app_labels.append(friendly)
            else:
                activities.append(0)
                bar_colors.append('#555555')
                app_labels.append('')
        
        bars = ax.bar(x, activities, color=bar_colors, alpha=0.8)
        
        # Add app name labels on bars
        for i, (bar, label) in enumerate(zip(bars, app_labels)):
            if label and bar.get_height() > 0:
                # Truncate long names
                display_label = label[:12] + '...' if len(label) > 12 else label
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(activities)*0.02,
                       display_label, ha='center', va='bottom', fontsize=8, color='#dddddd',
                       rotation=45)
        
        self.set_common_style(ax, tr('history.chart.top_apps_weekday'))
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel(tr('history.legend.activity'))

    def plot_top_apps_hourly(self, ax):
        """Plot most used app for each hour of day."""
        import numpy as np
        
        data = self.db.get_top_app_by_hour()
        
        if not data:
            ax.text(0.5, 0.5, tr('history.no_data'), ha='center', va='center', 
                    color='gray', fontsize=14, transform=ax.transAxes)
            ax.set_facecolor('#1e1e1e')
            return
        
        # Get metadata for friendly names
        metadata = self.db.get_app_metadata_dict()
        
        # Build data for all 24 hours
        data_map = {r[0]: r for r in data}  # hour -> (hour, app_name, activity)
        
        # Collect unique apps to assign colors
        unique_apps = list(set(r[1] for r in data))
        color_palette = ['#00e676', '#2196f3', '#ff9800', '#e91e63', '#9c27b0', '#00bcd4', '#ffeb3b']
        app_colors = {app: color_palette[i % len(color_palette)] for i, app in enumerate(unique_apps)}
        
        hours = list(range(24))
        activities = []
        bar_colors = []
        
        for h in hours:
            if h in data_map:
                _, app_name, activity = data_map[h]
                activities.append(activity or 0)
                bar_colors.append(app_colors[app_name])
            else:
                activities.append(0)
                bar_colors.append('#555555')
        
        ax.bar(hours, activities, color=bar_colors, alpha=0.8)
        
        # Build legend for unique apps
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=app_colors[app], alpha=0.8, 
                                label=metadata.get(app, {}).get('friendly_name') or app[:15])
                         for app in unique_apps]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8,
                 framealpha=0.7, facecolor='#2d2d2d')
        
        self.set_common_style(ax, tr('history.chart.top_apps_hourly'))
        ax.set_xticks(hours[::2])
        ax.set_xlabel('Hour')
        ax.set_ylabel(tr('history.legend.activity'))

class HistoryChartWidget(QWidget):
    """Main History Widget with Filter and Sub-charts."""
    def __init__(self, database):
        super().__init__()
        self.db = database
        # Map friendly name -> app_name
        self.app_map = {} 
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # --- Combined Top Bar: Tabs (left) + Filter (right) ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(20)
        
        # Tab Navigation (left side)
        self.btn_timeline = QPushButton(tr('history.timeline'))
        self.btn_timeline.setCheckable(True)
        self.btn_timeline.setChecked(True)
        self.btn_timeline.setStyleSheet(BTN_STYLE_TAB)
        self.btn_timeline.clicked.connect(lambda: self.switch_view(0))
        
        self.btn_insights = QPushButton(tr('history.insights'))
        self.btn_insights.setCheckable(True)
        self.btn_insights.setStyleSheet(BTN_STYLE_TAB)
        self.btn_insights.clicked.connect(lambda: self.switch_view(1))
        
        top_bar.addWidget(self.btn_timeline)
        top_bar.addWidget(self.btn_insights)
        top_bar.addStretch()  # Push scope filter to right
        
        # Scope Filter (right side)
        lbl_scope = QLabel(tr('history.scope'))
        lbl_scope.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        top_bar.addWidget(lbl_scope)
        
        self.app_combo = QComboBox()
        self.app_combo.setStyleSheet(COMBO_STYLE)
        self.app_combo.currentTextChanged.connect(self.on_app_changed)
        top_bar.addWidget(self.app_combo)
        
        layout.addLayout(top_bar)
        
        # --- Stacked Content ---
        self.stack = QStackedWidget()
        
        self.timeline = TimelineWidget(self.db)
        self.stack.addWidget(self.timeline)
        
        self.insight = InsightWidget(self.db)
        self.stack.addWidget(self.insight)
        
        layout.addWidget(self.stack)
        
    def on_app_changed(self, text):
        # Resolve friendly name back to app_name key
        app_key = self.app_map.get(text)
        
        self.timeline.update_filter(app_key)
        self.insight.update_filter(app_key)
        
    def switch_view(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_timeline.setChecked(index == 0)
        self.btn_insights.setChecked(index == 1)
        
    def showEvent(self, event):
        """Refreshes app list when tab is shown."""
        current_text = self.app_combo.currentText()
        self.app_combo.blockSignals(True)
        self.app_combo.clear()
        
        # Rebuild Map
        # 1. Get all app keys
        app_keys = self.db.get_all_apps()
        # 2. Get metadata
        metadata = self.db.get_app_metadata_dict()
        
        self.app_map = {}
        
        # "All Applications"
        all_apps_text = tr('history.all_apps')
        self.app_combo.addItem(all_apps_text)
        self.app_map[all_apps_text] = None
        
        # Populate
        items = []
        for app in app_keys:
            friendly = metadata.get(app, {}).get('friendly_name')
            if friendly:
                display = friendly
            else:
                display = app
                
            self.app_map[display] = app
            items.append(display)
            
        items.sort()
        self.app_combo.addItems(items)
        
        # Restore selection
        if current_text in self.app_map:
            self.app_combo.setCurrentText(current_text)
            
        self.app_combo.blockSignals(False)
        
        # Initial refresh
        self.on_app_changed(self.app_combo.currentText())
        super().showEvent(event)

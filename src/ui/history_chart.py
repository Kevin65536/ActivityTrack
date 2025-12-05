"""
History Chart Widget - Displays daily keystroke/click trends using matplotlib
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import datetime


class HistoryChartWidget(QWidget):
    """Widget displaying daily input statistics as line charts."""
    
    def __init__(self, database):
        super().__init__()
        self.db = database
        self.current_range = 'week'  # Default to week view
        self.setup_ui()
        self.update_chart()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with title and range buttons
        header = QHBoxLayout()
        
        title = QLabel("Input History")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Range selector buttons
        self.buttons = {}
        for key, label in [('week', '7 Days'), ('month', '30 Days'), ('year', '1 Year')]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, k=key: self.on_range_selected(k))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #aaaaaa;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background-color: #4a4a4a; }
                QPushButton:checked {
                    background-color: #00e676;
                    color: #1e1e1e;
                    font-weight: bold;
                }
            """)
            self.buttons[key] = btn
            header.addWidget(btn)
        
        self.buttons['week'].setChecked(True)
        layout.addLayout(header)
        
        # Matplotlib figure with dark theme
        plt.style.use('dark_background')
        self.figure = Figure(figsize=(10, 5), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(self.canvas)
    
    def on_range_selected(self, key):
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)
        self.current_range = key
        self.update_chart()
    
    def get_date_range(self):
        today = datetime.date.today()
        if self.current_range == 'week':
            return today - datetime.timedelta(days=6), today
        elif self.current_range == 'month':
            return today - datetime.timedelta(days=29), today
        else:  # year
            return today - datetime.timedelta(days=364), today
    
    def update_chart(self):
        start_date, end_date = self.get_date_range()
        data = self.db.get_daily_history(start_date, end_date)
        
        # Clear figure
        self.figure.clear()
        
        if not data:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', 
                   ha='center', va='center', fontsize=16, color='#aaaaaa')
            ax.set_facecolor('#1e1e1e')
            self.canvas.draw()
            return
        
        # Parse data
        dates = [row[0] for row in data]
        keys = [row[1] for row in data]
        clicks = [row[2] for row in data]
        
        # Convert string dates to datetime if needed
        if isinstance(dates[0], str):
            dates = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
        
        # Create subplot
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1e1e1e')
        
        # Plot lines
        line_keys, = ax.plot(dates, keys, 'o-', color='#00e676', linewidth=2, 
                            markersize=6, label='Keystrokes')
        line_clicks, = ax.plot(dates, clicks, 's-', color='#2196f3', linewidth=2, 
                              markersize=6, label='Clicks')
        
        # Style axes
        ax.set_xlabel('Date', color='#aaaaaa', fontsize=12)
        ax.set_ylabel('Count', color='#aaaaaa', fontsize=12)
        ax.tick_params(colors='#aaaaaa')
        ax.spines['bottom'].set_color('#3d3d3d')
        ax.spines['left'].set_color('#3d3d3d')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.2, color='#ffffff')
        
        # Legend
        ax.legend(loc='upper left', facecolor='#2b2b2b', edgecolor='#3d3d3d',
                 labelcolor='#ffffff')
        
        # Rotate date labels for readability
        self.figure.autofmt_xdate(rotation=45)
        
        # Tight layout
        self.figure.tight_layout()
        
        self.canvas.draw()

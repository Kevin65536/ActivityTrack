from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                                 QTableWidgetItem, QHeaderView, QLabel, QFileIconProvider)
from PySide6.QtCore import Qt, QFileInfo
from ..i18n import tr

class AppStatsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table Setup
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr('apps.header.application'), 
            tr('apps.header.keys'), 
            tr('apps.header.clicks'), 
            tr('apps.header.scrolls'), 
            tr('apps.header.distance')
        ])
        
        # Styling
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # App name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                gridline-color: #333333;
                border: none;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #aaaaaa;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #00bcd4;
                color: black;
            }
        """)
        
        layout.addWidget(self.table)
        
    def update_data(self, data, metadata=None):
        """
        Update table with list of tuples: (app_name, keys, clicks, scrolls, distance)
        metadata: dict {app_name: {'friendly_name': str, 'exe_path': str}}
        """
        metadata = metadata or {}
        icon_provider = QFileIconProvider()
        
        self.table.setSortingEnabled(False) # Disable sorting while updating
        self.table.setRowCount(len(data))
        
        for row, (app, keys, clicks, scrolls, dist) in enumerate(data):
            # Resolve Metadata
            friendly_name = app
            exe_path = None
            if app in metadata:
                meta = metadata[app]
                friendly_name = meta.get('friendly_name') or app
                exe_path = meta.get('exe_path')
            
            # App Name Item with Icon
            name_item = QTableWidgetItem(str(friendly_name))
            
            # Load Icon
            if exe_path:
                info = QFileInfo(exe_path)
                icon = icon_provider.icon(info)
                if not icon.isNull():
                    name_item.setIcon(icon)
            
            name_item.setToolTip(app) # Show real exe name on hover
            self.table.setItem(row, 0, name_item)
            
            # Keys
            keys_item = QTableWidgetItem()
            keys_item.setData(Qt.DisplayRole, keys)
            self.table.setItem(row, 1, keys_item)
            
            # Clicks
            clicks_item = QTableWidgetItem()
            clicks_item.setData(Qt.DisplayRole, clicks)
            self.table.setItem(row, 2, clicks_item)
            
            # Scrolls
            scrolls_item = QTableWidgetItem()
            scrolls_item.setData(Qt.DisplayRole, scrolls)
            self.table.setItem(row, 3, scrolls_item)
            
            # Distance
            dist_str = f"{dist:.2f}m"
            dist_item = QTableWidgetItem()
            dist_item.setData(Qt.DisplayRole, dist) # Sort by value
            dist_item.setText(dist_str) # Display string
            self.table.setItem(row, 4, dist_item)
            
        self.table.setSortingEnabled(True) # Re-enable sorting

"""
Settings page UI for ActivityTrack.
Provides controls for autostart, data retention, theme selection, etc.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QCheckBox, QComboBox, QSpinBox, QPushButton, QGroupBox,
    QFormLayout, QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPen

from ..config import Config, HEATMAP_THEMES, get_theme_color


class ColorPreviewWidget(QWidget):
    """Widget to preview heatmap color gradient."""
    
    def __init__(self, theme_name='default'):
        super().__init__()
        self.theme_name = theme_name
        self.setFixedHeight(30)
        self.setMinimumWidth(200)
    
    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw gradient bar
        width = self.width() - 4
        height = self.height() - 4
        
        for x in range(width):
            ratio = x / max(width - 1, 1)
            r, g, b = get_theme_color(self.theme_name, ratio)
            painter.setPen(QPen(QColor(r, g, b)))
            painter.drawLine(x + 2, 2, x + 2, height + 2)
        
        # Draw border
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 3, 3)


class SettingsWidget(QWidget):
    """Settings page with all configuration options."""
    
    # Signal emitted when theme changes (for live preview)
    theme_changed = Signal(str)
    settings_changed = Signal()
    
    def __init__(self, config: Config = None, database=None):
        super().__init__()
        self.config = config or Config()
        self.database = database
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the settings UI."""
        # Main layout with scroll area for many settings
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: white;")
        main_layout.addWidget(title)
        
        # Scroll area for settings groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        # General Settings Group
        general_group = self.create_group("General")
        general_layout = QVBoxLayout()
        general_layout.setSpacing(15)
        
        # Autostart checkbox
        self.autostart_check = QCheckBox("Start with Windows")
        self.autostart_check.setStyleSheet(self.get_checkbox_style())
        self.autostart_check.stateChanged.connect(self.on_autostart_changed)
        general_layout.addWidget(self.autostart_check)
        
        # Autostart hint label (shown only in dev mode)
        self.autostart_hint = QLabel("(Only available in packaged .exe version)")
        self.autostart_hint.setStyleSheet("color: #888888; font-size: 12px; margin-left: 30px;")
        self.autostart_hint.setVisible(not self.config.is_frozen())
        general_layout.addWidget(self.autostart_hint)
        
        # Disable autostart checkbox in dev mode
        if not self.config.is_frozen():
            self.autostart_check.setEnabled(False)
            self.autostart_check.setToolTip("Autostart is only available when running as a packaged executable (.exe)")
        
        # Minimize to tray checkbox
        self.minimize_tray_check = QCheckBox("Minimize to system tray instead of closing")
        self.minimize_tray_check.setStyleSheet(self.get_checkbox_style())
        self.minimize_tray_check.stateChanged.connect(self.on_minimize_tray_changed)
        general_layout.addWidget(self.minimize_tray_check)
        
        general_group.setLayout(general_layout)
        scroll_layout.addWidget(general_group)
        
        # Data Management Group
        data_group = self.create_group("Data Management")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(15)
        
        # Data retention setting
        retention_layout = QHBoxLayout()
        retention_label = QLabel("Keep data for:")
        retention_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        retention_layout.addWidget(retention_label)
        
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(-1, 3650)  # -1 = forever, up to 10 years
        self.retention_spin.setSpecialValueText("Forever")
        self.retention_spin.setSuffix(" days")
        self.retention_spin.setStyleSheet(self.get_spinbox_style())
        self.retention_spin.setFixedWidth(120)
        self.retention_spin.valueChanged.connect(self.on_retention_changed)
        retention_layout.addWidget(self.retention_spin)
        
        retention_layout.addStretch()
        data_layout.addLayout(retention_layout)
        
        # Data retention hint
        retention_hint = QLabel("Set to -1 or 'Forever' to keep all data indefinitely.")
        retention_hint.setStyleSheet("color: #888888; font-size: 12px;")
        data_layout.addWidget(retention_hint)
        
        # Separator
        data_layout.addSpacing(10)
        
        # Clear data button
        clear_layout = QHBoxLayout()
        clear_label = QLabel("Clear all tracking data:")
        clear_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        clear_layout.addWidget(clear_label)
        
        self.clear_data_btn = QPushButton("Clear Data")
        self.clear_data_btn.setStyleSheet(self.get_danger_button_style())
        self.clear_data_btn.setFixedWidth(120)
        self.clear_data_btn.clicked.connect(self.on_clear_data)
        clear_layout.addWidget(self.clear_data_btn)
        
        clear_layout.addStretch()
        data_layout.addLayout(clear_layout)
        
        data_group.setLayout(data_layout)
        scroll_layout.addWidget(data_group)
        
        # Appearance Group
        appearance_group = self.create_group("Appearance")
        appearance_layout = QVBoxLayout()
        appearance_layout.setSpacing(15)
        
        # Heatmap theme selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Heatmap color theme:")
        theme_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet(self.get_combobox_style())
        self.theme_combo.setMinimumWidth(280)
        
        # Add themes to combo
        for theme_key, theme_data in HEATMAP_THEMES.items():
            self.theme_combo.addItem(theme_data['name'], theme_key)
        
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        appearance_layout.addLayout(theme_layout)
        
        # Theme preview
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        preview_layout.addWidget(preview_label)
        
        self.theme_preview = ColorPreviewWidget()
        preview_layout.addWidget(self.theme_preview)
        preview_layout.addStretch()
        
        appearance_layout.addLayout(preview_layout)
        
        appearance_group.setLayout(appearance_layout)
        scroll_layout.addWidget(appearance_group)
        
        # Add stretch at the end
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def create_group(self, title):
        """Create a styled group box."""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                font-size: 15px;
                font-weight: bold;
                color: #00e676;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        return group
    
    def get_checkbox_style(self):
        return """
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #4a4a4a;
                background-color: #2b2b2b;
            }
            QCheckBox::indicator:hover {
                border-color: #00e676;
            }
            QCheckBox::indicator:checked {
                background-color: #00e676;
                border-color: #00e676;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00c853;
            }
        """
    
    def get_spinbox_style(self):
        return """
            QSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QSpinBox:focus {
                border-color: #00e676;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a4a4a;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid #aaaaaa;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #aaaaaa;
            }
        """
    
    def get_combobox_style(self):
        return """
            QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #00e676;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #aaaaaa;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #00e676;
                selection-color: #1e1e1e;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3d3d3d;
            }
        """
    
    def get_danger_button_style(self):
        return """
            QPushButton {
                background-color: #c62828;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """
    
    def load_settings(self):
        """Load current settings into UI controls."""
        # Block signals while loading
        self.autostart_check.blockSignals(True)
        self.minimize_tray_check.blockSignals(True)
        self.retention_spin.blockSignals(True)
        self.theme_combo.blockSignals(True)
        
        # Load values from config (trust config file, not registry)
        self.autostart_check.setChecked(self.config.autostart)
        self.minimize_tray_check.setChecked(self.config.minimize_to_tray)
        self.retention_spin.setValue(self.config.data_retention_days)
        
        # Set theme combo
        current_theme = self.config.heatmap_theme
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        self.theme_preview.set_theme(current_theme)
        
        # Unblock signals
        self.autostart_check.blockSignals(False)
        self.minimize_tray_check.blockSignals(False)
        self.retention_spin.blockSignals(False)
        self.theme_combo.blockSignals(False)
    
    def on_autostart_changed(self, state):
        """Handle autostart checkbox change."""
        # Note: In PySide6, stateChanged sends int (0, 1, 2), not Qt.CheckState enum
        # Qt.Checked.value == 2, Qt.Unchecked.value == 0
        enabled = (state == Qt.Checked.value)
        
        # Set the value - this returns (success, error_message)
        result = self.config.__class__.autostart.fset(self.config, enabled)
        
        if result and not result[0]:
            # Registry update failed - show error and revert checkbox
            QMessageBox.warning(
                self,
                "Autostart Error",
                f"Failed to update Windows startup settings:\n\n{result[1]}\n\n"
                "The setting has been reverted."
            )
            # Revert checkbox to actual state
            self.autostart_check.blockSignals(True)
            self.autostart_check.setChecked(self.config.autostart)
            self.autostart_check.blockSignals(False)
        
        self.settings_changed.emit()
    
    def on_minimize_tray_changed(self, state):
        """Handle minimize to tray checkbox change."""
        # Note: In PySide6, stateChanged sends int (0, 1, 2), not Qt.CheckState enum
        self.config.minimize_to_tray = (state == Qt.Checked.value)
        self.settings_changed.emit()
    
    def on_retention_changed(self, value):
        """Handle data retention spinbox change."""
        self.config.data_retention_days = value
        self.settings_changed.emit()
    
    def on_theme_changed(self, index):
        """Handle theme combo change."""
        theme_key = self.theme_combo.itemData(index)
        self.config.heatmap_theme = theme_key
        self.theme_preview.set_theme(theme_key)
        self.theme_changed.emit(theme_key)
        self.settings_changed.emit()
    
    def on_clear_data(self):
        """Handle clear data button click."""
        reply = QMessageBox.warning(
            self,
            "Clear All Data",
            "Are you sure you want to delete all tracking data?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Confirm again for safety
            reply2 = QMessageBox.critical(
                self,
                "Confirm Delete",
                "This will permanently delete:\n"
                "• All keystroke statistics\n"
                "• All mouse click data\n"
                "• All heatmap data\n"
                "• All application statistics\n\n"
                "Are you absolutely sure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply2 == QMessageBox.Yes:
                self.clear_all_data()
    
    def clear_all_data(self):
        """Clear all data from database."""
        if self.database:
            try:
                with self.database.get_connection() as conn:
                    cursor = conn.cursor()
                    # Clear all tables
                    cursor.execute("DELETE FROM daily_stats")
                    cursor.execute("DELETE FROM app_stats")
                    cursor.execute("DELETE FROM heatmap_data")
                    cursor.execute("DELETE FROM mouse_heatmap_data")
                    cursor.execute("DELETE FROM app_heatmap_data")
                    cursor.execute("DELETE FROM app_mouse_heatmap_data")
                    cursor.execute("DELETE FROM hourly_app_stats")
                    # Keep app_metadata as it's just friendly names
                    conn.commit()
                
                QMessageBox.information(
                    self,
                    "Data Cleared",
                    "All tracking data has been deleted successfully."
                )
                self.settings_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear data: {str(e)}"
                )
        else:
            QMessageBox.warning(
                self,
                "Warning",
                "Database not available. Cannot clear data."
            )

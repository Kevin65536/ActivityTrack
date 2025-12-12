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
from ..i18n import tr, get_i18n, get_supported_languages, set_language


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
    language_changed = Signal(str)
    
    def __init__(self, config: Config = None, database=None):
        super().__init__()
        self.config = config or Config()
        self.database = database
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the settings UI."""
        # Force dark theme for ALL child widgets to prevent system theme interference
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                background-color: transparent;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                padding-top: 12px;
                font-size: 15px;
                font-weight: bold;
                color: #00e676;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: 0px;
                padding: 2px 8px;
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QCheckBox {
                background-color: transparent;
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
            QCheckBox:disabled {
                color: #666666;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QSpinBox {
                background-color: #3d3d3d;
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
                background-color: #4a4a4a;
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #5a5a5a;
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
            QComboBox {
                background-color: #3d3d3d;
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
                background-color: #2b2b2b;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3d3d3d;
            }
            QPushButton#clearDataBtn {
                background-color: #c62828;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#clearDataBtn:hover {
                background-color: #e53935;
            }
            QPushButton#clearDataBtn:pressed {
                background-color: #b71c1c;
            }
        """)
        
        # Main layout with scroll area for many settings
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Title
        self.title_label = QLabel(tr('settings.title'))
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.title_label)
        
        # Scroll area for settings groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        # General Settings Group
        self.general_group = self.create_group(tr('settings.general'))
        general_layout = QVBoxLayout()
        general_layout.setSpacing(15)
        
        # Autostart checkbox
        self.autostart_check = QCheckBox(tr('settings.autostart'))
        self.autostart_check.stateChanged.connect(self.on_autostart_changed)
        general_layout.addWidget(self.autostart_check)
        
        # Autostart hint label (shown only in dev mode)
        self.autostart_hint = QLabel(tr('settings.autostart_hint'))
        self.autostart_hint.setStyleSheet("color: #888888; font-size: 12px; margin-left: 30px; background-color: transparent;")
        self.autostart_hint.setVisible(not self.config.is_frozen())
        general_layout.addWidget(self.autostart_hint)
        
        # Disable autostart checkbox in dev mode
        if not self.config.is_frozen():
            self.autostart_check.setEnabled(False)
            self.autostart_check.setToolTip(tr('settings.autostart_tooltip'))
        
        # Minimize to tray checkbox
        self.minimize_tray_check = QCheckBox(tr('settings.minimize_tray'))
        self.minimize_tray_check.stateChanged.connect(self.on_minimize_tray_changed)
        general_layout.addWidget(self.minimize_tray_check)
        
        self.general_group.setLayout(general_layout)
        scroll_layout.addWidget(self.general_group)
        
        # Data Management Group
        self.data_group = self.create_group(tr('settings.data_management'))
        data_layout = QVBoxLayout()
        data_layout.setSpacing(15)
        
        # Data retention setting
        retention_layout = QHBoxLayout()
        self.retention_label = QLabel(tr('settings.retention'))
        self.retention_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        retention_layout.addWidget(self.retention_label)
        
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(-1, 3650)  # -1 = forever, up to 10 years
        self.retention_spin.setSpecialValueText(tr('settings.retention_forever'))
        self.retention_spin.setSuffix(tr('settings.retention_days'))
        self.retention_spin.setFixedWidth(120)
        self.retention_spin.valueChanged.connect(self.on_retention_changed)
        retention_layout.addWidget(self.retention_spin)
        
        retention_layout.addStretch()
        data_layout.addLayout(retention_layout)
        
        # Data retention hint
        self.retention_hint = QLabel(tr('settings.retention_hint'))
        self.retention_hint.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
        data_layout.addWidget(self.retention_hint)
        
        # Separator
        data_layout.addSpacing(10)
        
        # Clear data button
        clear_layout = QHBoxLayout()
        self.clear_label = QLabel(tr('settings.clear_data'))
        self.clear_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        clear_layout.addWidget(self.clear_label)
        
        self.clear_data_btn = QPushButton(tr('settings.clear_data_btn'))
        self.clear_data_btn.setObjectName("clearDataBtn")
        self.clear_data_btn.setFixedWidth(120)
        self.clear_data_btn.clicked.connect(self.on_clear_data)
        clear_layout.addWidget(self.clear_data_btn)
        
        clear_layout.addStretch()
        data_layout.addLayout(clear_layout)
        
        self.data_group.setLayout(data_layout)
        scroll_layout.addWidget(self.data_group)
        
        # Idle Detection Group
        self.idle_group = self.create_group(tr('settings.idle_detection'))
        idle_layout = QVBoxLayout()
        idle_layout.setSpacing(15)
        
        # Idle timeout setting
        idle_timeout_layout = QHBoxLayout()
        self.idle_timeout_label = QLabel(tr('settings.idle_timeout'))
        self.idle_timeout_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        idle_timeout_layout.addWidget(self.idle_timeout_label)
        
        self.idle_timeout_spin = QSpinBox()
        self.idle_timeout_spin.setRange(0, 60)  # 0 = disabled, up to 60 minutes
        self.idle_timeout_spin.setSpecialValueText(tr('settings.idle_disabled'))
        self.idle_timeout_spin.setSuffix(tr('settings.idle_minutes'))
        self.idle_timeout_spin.setFixedWidth(120)
        self.idle_timeout_spin.valueChanged.connect(self.on_idle_timeout_changed)
        idle_timeout_layout.addWidget(self.idle_timeout_spin)
        
        idle_timeout_layout.addStretch()
        idle_layout.addLayout(idle_timeout_layout)
        
        # Idle timeout hint
        self.idle_timeout_hint = QLabel(tr('settings.idle_timeout_hint'))
        self.idle_timeout_hint.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
        idle_layout.addWidget(self.idle_timeout_hint)
        
        self.idle_group.setLayout(idle_layout)
        scroll_layout.addWidget(self.idle_group)
        
        # Appearance Group
        self.appearance_group = self.create_group(tr('settings.appearance'))
        appearance_layout = QVBoxLayout()
        appearance_layout.setSpacing(15)
        
        # Language selector
        language_layout = QHBoxLayout()
        self.language_label = QLabel(tr('settings.language'))
        self.language_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        language_layout.addWidget(self.language_label)
        
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(200)
        
        # Add languages to combo
        for lang_code, lang_name in get_supported_languages().items():
            self.language_combo.addItem(lang_name, lang_code)
        
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        
        appearance_layout.addLayout(language_layout)
        
        # Language change hint
        self.language_hint = QLabel(tr('settings.language_hint'))
        self.language_hint.setStyleSheet("color: #888888; font-size: 12px; background-color: transparent;")
        appearance_layout.addWidget(self.language_hint)
        
        appearance_layout.addSpacing(10)
        
        # Heatmap theme selector
        theme_layout = QHBoxLayout()
        self.theme_label = QLabel(tr('settings.theme'))
        self.theme_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")
        theme_layout.addWidget(self.theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(280)
        
        # Add themes to combo
        for theme_key in HEATMAP_THEMES.keys():
            self.theme_combo.addItem(tr(f'theme.{theme_key}'), theme_key)
        
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        appearance_layout.addLayout(theme_layout)
        
        # Theme preview
        preview_layout = QHBoxLayout()
        self.preview_label = QLabel(tr('settings.preview'))
        self.preview_label.setStyleSheet("color: #aaaaaa; font-size: 13px; background-color: transparent;")
        preview_layout.addWidget(self.preview_label)
        
        self.theme_preview = ColorPreviewWidget()
        preview_layout.addWidget(self.theme_preview)
        preview_layout.addStretch()
        
        appearance_layout.addLayout(preview_layout)
        
        self.appearance_group.setLayout(appearance_layout)
        scroll_layout.addWidget(self.appearance_group)
        
        # Add stretch at the end
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def create_group(self, title):
        """Create a styled group box."""
        group = QGroupBox(title)
        return group
    
    def retranslate_ui(self):
        """Update all UI text for current language."""
        self.title_label.setText(tr('settings.title'))
        
        # General group
        self.general_group.setTitle(tr('settings.general'))
        self.autostart_check.setText(tr('settings.autostart'))
        self.autostart_hint.setText(tr('settings.autostart_hint'))
        if not self.config.is_frozen():
            self.autostart_check.setToolTip(tr('settings.autostart_tooltip'))
        self.minimize_tray_check.setText(tr('settings.minimize_tray'))
        
        # Data management group
        self.data_group.setTitle(tr('settings.data_management'))
        self.retention_label.setText(tr('settings.retention'))
        self.retention_spin.setSpecialValueText(tr('settings.retention_forever'))
        self.retention_spin.setSuffix(tr('settings.retention_days'))
        self.retention_hint.setText(tr('settings.retention_hint'))
        self.clear_label.setText(tr('settings.clear_data'))
        self.clear_data_btn.setText(tr('settings.clear_data_btn'))
        
        # Idle detection group
        self.idle_group.setTitle(tr('settings.idle_detection'))
        self.idle_timeout_label.setText(tr('settings.idle_timeout'))
        self.idle_timeout_spin.setSpecialValueText(tr('settings.idle_disabled'))
        self.idle_timeout_spin.setSuffix(tr('settings.idle_minutes'))
        self.idle_timeout_hint.setText(tr('settings.idle_timeout_hint'))
        
        # Appearance group
        self.appearance_group.setTitle(tr('settings.appearance'))
        self.language_label.setText(tr('settings.language'))
        self.language_hint.setText(tr('settings.language_hint'))
        self.theme_label.setText(tr('settings.theme'))
        self.preview_label.setText(tr('settings.preview'))
        
        # Update theme combo items
        current_theme = self.theme_combo.currentData()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for theme_key in HEATMAP_THEMES.keys():
            self.theme_combo.addItem(tr(f'theme.{theme_key}'), theme_key)
        # Restore selection
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        self.theme_combo.blockSignals(False)
    
    def load_settings(self):
        """Load current settings into UI controls."""
        # Block signals while loading
        self.autostart_check.blockSignals(True)
        self.minimize_tray_check.blockSignals(True)
        self.retention_spin.blockSignals(True)
        self.theme_combo.blockSignals(True)
        self.language_combo.blockSignals(True)
        self.idle_timeout_spin.blockSignals(True)
        
        # Load values from config (trust config file, not registry)
        self.autostart_check.setChecked(self.config.autostart)
        self.minimize_tray_check.setChecked(self.config.minimize_to_tray)
        self.retention_spin.setValue(self.config.data_retention_days)
        
        # Load idle timeout (convert seconds to minutes for display)
        idle_seconds = self.config.idle_timeout_seconds
        self.idle_timeout_spin.setValue(idle_seconds // 60)
        
        # Set language combo
        current_lang = self.config.language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
        
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
        self.language_combo.blockSignals(False)
        self.idle_timeout_spin.blockSignals(False)
    
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
                tr('dialog.autostart_error.title'),
                tr('dialog.autostart_error.message', error=result[1])
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
    
    def on_idle_timeout_changed(self, value):
        """Handle idle timeout spinbox change."""
        # Convert minutes to seconds for storage
        self.config.idle_timeout_seconds = value * 60
        self.settings_changed.emit()
    
    def on_language_changed(self, index):
        """Handle language combo change."""
        lang_code = self.language_combo.itemData(index)
        if lang_code and lang_code != self.config.language:
            self.config.language = lang_code
            set_language(lang_code)
            self.language_changed.emit(lang_code)
            self.settings_changed.emit()
            
            # Show restart hint
            QMessageBox.information(
                self,
                tr('dialog.language_change.title'),
                tr('dialog.language_change.message')
            )
    
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
            tr('dialog.clear_data.title'),
            tr('dialog.clear_data.message'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Confirm again for safety
            reply2 = QMessageBox.critical(
                self,
                tr('dialog.clear_data.confirm_title'),
                tr('dialog.clear_data.confirm_message'),
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
                    tr('dialog.clear_data.success_title'),
                    tr('dialog.clear_data.success_message')
                )
                self.settings_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    tr('dialog.clear_data.error_title'),
                    tr('dialog.clear_data.error_message', error=str(e))
                )
        else:
            QMessageBox.warning(
                self,
                tr('dialog.clear_data.warning_title'),
                tr('dialog.clear_data.warning_message')
            )

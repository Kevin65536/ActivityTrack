"""
Configuration management for ActivityTrack.
Handles persistent settings like autostart, data retention, and theme preferences.
"""

import json
import copy
import logging
from .fileio import atomic_text_file
import os
import sys
import winreg

# Default configuration values
DEFAULT_CONFIG = {
    'autostart': False,
    'data_retention_days': 365,  # -1 means keep forever
    'heatmap_theme': 'default',  # 'default', 'fire', 'ocean', 'monochrome'
    'keyboard_layout': 'tkl',  # 'full', 'tkl', '75', '60'
    'minimize_to_tray': True,
    'show_notifications': True,
    'language': 'en',  # 'en' for English, 'zh' for Chinese
    'idle_timeout_seconds': 300,  # 5 minutes, 0 to disable idle detection
    # Break reminder settings
    'break_reminder_enabled': True,  # Enable/disable break reminders
    'break_reminder_interval_minutes': 45,  # Time in minutes before reminder (0 to disable)
    'break_reminder_duration_minutes': 5,  # Suggested break duration in minutes
    # App grouping settings
    'app_groups': {
        'productivity': [],  # List of app names considered productive
        'other': [],  # List of app names considered other/leisure
    },
    'screen_time_group_display': False,  # False = show individual apps, True = show category groups
}

CONFIG_FILE = 'config.json'

# Registry key for Windows autostart
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ActivityTrack"


class Config:
    """Configuration manager with file persistence and autostart support."""
    
    def __init__(self, config_dir=None):
        """Initialize config manager.
        
        Args:
            config_dir: Directory to store config file. Defaults to app directory.
        """
        if config_dir is None:
            # Use app directory (where the script is located)
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                config_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, CONFIG_FILE)
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self.load_error = None
        self.load()
    
    @staticmethod
    def _validate(key, value):
        if key not in DEFAULT_CONFIG:
            raise ValueError(f'Unknown setting: {key}')
        default = DEFAULT_CONFIG[key]
        if type(default) is bool:
            valid = type(value) is bool
        elif type(default) is int:
            ranges = {'data_retention_days': (-1, 3650), 'idle_timeout_seconds': (0, 3600),
                      'break_reminder_interval_minutes': (0, 180),
                      'break_reminder_duration_minutes': (1, 30)}
            low, high = ranges[key]
            valid = type(value) is int and low <= value <= high
            if key == 'data_retention_days' and value == 0:
                value = -1  # Historical zero had no pruning semantics.
        elif key == 'app_groups':
            valid = isinstance(value, dict) and all(
                isinstance(value.get(group, []), list) and all(isinstance(item, str) for item in value.get(group, []))
                for group in ('productivity', 'other'))
            if valid:
                value = {group: list(dict.fromkeys(value.get(group, []))) for group in ('productivity', 'other')}
        else:
            allowed = {'heatmap_theme': HEATMAP_THEMES, 'keyboard_layout': ('full', 'tkl', '75', '60'),
                       'language': ('en', 'zh')}
            valid = isinstance(value, str) and value in allowed[key]
        if not valid:
            raise ValueError(f'Invalid value for {key}')
        return copy.deepcopy(value)

    def load(self):
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self.load_error = None
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as stream:
                    saved = json.load(stream)
                if not isinstance(saved, dict):
                    raise ValueError('Configuration must be a JSON object')
                invalid = []
                for key, value in saved.items():
                    if key in DEFAULT_CONFIG:
                        try:
                            self._config[key] = self._validate(key, value)
                        except ValueError:
                            invalid.append(key)
                if invalid:
                    raise ValueError('Invalid settings replaced by defaults: ' + ', '.join(invalid))
        except (OSError, ValueError) as error:
            self.load_error = str(error)
            logging.getLogger(__name__).warning('Configuration could not be fully loaded: %s', error)

    def save(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with atomic_text_file(self.config_path) as stream:
            json.dump(self._config, stream, indent=2, ensure_ascii=False)
            stream.write('\n')

    def get(self, key, default=None):
        return copy.deepcopy(self._config.get(key, default))

    def set(self, key, value):
        value = self._validate(key, value)
        previous = self._config[key]
        self._config[key] = value
        try:
            self.save()
        except Exception:
            self._config[key] = previous
            raise

    # Property accessors for common settings
    @property
    def autostart(self):
        return self._config.get('autostart', False)
    
    @autostart.setter
    def autostart(self, value):
        value = self._validate('autostart', value)
        previous = self.is_autostart_enabled()
        result = self._update_autostart_registry(value)
        if result[0]:
            try:
                self.set('autostart', value)
            except OSError as error:
                rollback = self._update_autostart_registry(previous)
                self._config['autostart'] = self.is_autostart_enabled()
                result = (False, str(error) + ('' if rollback[0] else '; ' + rollback[1]))
        self._last_autostart_result = result
        return result

    @property
    def data_retention_days(self):
        return self._config.get('data_retention_days', 365)
    
    @data_retention_days.setter
    def data_retention_days(self, value):
        self.set('data_retention_days', value)
    
    @property
    def heatmap_theme(self):
        return self._config.get('heatmap_theme', 'default')
    
    @heatmap_theme.setter
    def heatmap_theme(self, value):
        self.set('heatmap_theme', value)
    
    @property
    def keyboard_layout(self):
        return self._config.get('keyboard_layout', 'tkl')
    
    @keyboard_layout.setter
    def keyboard_layout(self, value):
        self.set('keyboard_layout', value)
    
    @property
    def minimize_to_tray(self):
        return self._config.get('minimize_to_tray', True)
    
    @minimize_to_tray.setter
    def minimize_to_tray(self, value):
        self.set('minimize_to_tray', value)
    
    @property
    def show_notifications(self):
        return self._config.get('show_notifications', True)
    
    @show_notifications.setter
    def show_notifications(self, value):
        self.set('show_notifications', value)
    
    @property
    def language(self):
        return self._config.get('language', 'en')
    
    @language.setter
    def language(self, value):
        self.set('language', value)
    
    @property
    def idle_timeout_seconds(self):
        return self._config.get('idle_timeout_seconds', 300)
    
    @idle_timeout_seconds.setter
    def idle_timeout_seconds(self, value):
        self.set('idle_timeout_seconds', value)
    
    @property
    def break_reminder_enabled(self):
        return self._config.get('break_reminder_enabled', True)
    
    @break_reminder_enabled.setter
    def break_reminder_enabled(self, value):
        self.set('break_reminder_enabled', value)
    
    @property
    def break_reminder_interval_minutes(self):
        return self._config.get('break_reminder_interval_minutes', 45)
    
    @break_reminder_interval_minutes.setter
    def break_reminder_interval_minutes(self, value):
        self.set('break_reminder_interval_minutes', value)
    
    @property
    def break_reminder_duration_minutes(self):
        return self._config.get('break_reminder_duration_minutes', 5)
    
    @break_reminder_duration_minutes.setter
    def break_reminder_duration_minutes(self, value):
        self.set('break_reminder_duration_minutes', value)
    
    @property
    def app_groups(self):
        """Get app groups configuration."""
        return self.get('app_groups')
    
    @app_groups.setter
    def app_groups(self, value):
        """Set app groups configuration."""
        self.set('app_groups', value)
    
    @property
    def screen_time_group_display(self):
        """Get screen time group display mode. False = individual apps, True = category groups."""
        return self._config.get('screen_time_group_display', False)
    
    @screen_time_group_display.setter
    def screen_time_group_display(self, value):
        """Set screen time group display mode."""
        self.set('screen_time_group_display', value)
    
    def get_app_group(self, app_name):
        """Get the group for a specific app. Returns 'productivity', 'other', or None if unassigned."""
        groups = self.app_groups
        if app_name in groups.get('productivity', []):
            return 'productivity'
        elif app_name in groups.get('other', []):
            return 'other'
        return None
    
    def set_app_group(self, app_name, group):
        """Set the group for a specific app. group should be 'productivity', 'other', or None to remove."""
        groups = self.app_groups.copy()
        
        # Deep copy the lists
        groups = {
            'productivity': list(groups.get('productivity', [])),
            'other': list(groups.get('other', []))
        }
        
        # Remove from all groups first
        if app_name in groups['productivity']:
            groups['productivity'].remove(app_name)
        if app_name in groups['other']:
            groups['other'].remove(app_name)
        
        # Add to the specified group
        if group == 'productivity':
            groups['productivity'].append(app_name)
        elif group == 'other':
            groups['other'].append(app_name)
        
        self.app_groups = groups
    
    @staticmethod
    def is_frozen():
        """Check if running as a compiled executable (PyInstaller bundle)."""
        return getattr(sys, 'frozen', False)
    
    def _get_executable_path(self):
        """Get the path to the main executable.
        
        Returns:
            str or None: Path to executable if frozen, None if running as script.
        """
        if self.is_frozen():
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script - autostart not supported
            return None
    
    def _update_autostart_registry(self, enable):
        """Update Windows registry for autostart.
        
        Only works when running as a compiled executable (PyInstaller bundle).
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        # Only allow autostart for packaged executable
        if not self.is_frozen():
            if enable:
                error_msg = "Autostart is only available in the packaged version (.exe). Please build the application first."
                print(f"Warning: {error_msg}")
                return (False, error_msg)
            else:
                # Allow disabling even in dev mode (just remove any existing entry)
                pass
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                AUTOSTART_KEY,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            
            if enable:
                exe_path = self._get_executable_path()
                if exe_path is None:
                    winreg.CloseKey(key)
                    return (False, "Cannot determine executable path.")
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass  # Key doesn't exist, nothing to delete
            
            winreg.CloseKey(key)
            return (True, None)
        except PermissionError as e:
            error_msg = f"Permission denied when updating autostart registry: {e}"
            print(f"Warning: {error_msg}")
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Could not update autostart registry: {e}"
            print(f"Warning: {error_msg}")
            return (False, error_msg)
    
    def is_autostart_enabled(self):
        """Check if autostart is currently enabled in registry."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                AUTOSTART_KEY,
                0,
                winreg.KEY_QUERY_VALUE
            )
            try:
                winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False
    
    def sync_autostart_state(self):
        """Sync config autostart state with actual registry state."""
        actual_state = self.is_autostart_enabled()
        if self._config.get('autostart', False) != actual_state:
            self._config['autostart'] = actual_state
            self.save()
        return actual_state


# Heatmap color themes
HEATMAP_THEMES = {
    'default': {
        'name': 'Default (Blue → Green → Yellow → Orange)',
        'colors': [
            (0.00, (74, 111, 165)),    # Soft Blue
            (0.25, (74, 143, 143)),    # Teal
            (0.50, (107, 175, 107)),   # Soft Green
            (0.75, (212, 184, 90)),    # Warm Yellow
            (1.00, (212, 115, 107)),   # Soft Coral
        ]
    },
    'fire': {
        'name': 'Fire (Black → Red → Yellow → White)',
        'colors': [
            (0.00, (20, 20, 20)),      # Near Black
            (0.33, (180, 30, 30)),     # Dark Red
            (0.66, (255, 160, 50)),    # Orange
            (1.00, (255, 255, 200)),   # Light Yellow
        ]
    },
    'ocean': {
        'name': 'Ocean (Deep Blue → Cyan → White)',
        'colors': [
            (0.00, (10, 30, 80)),      # Deep Blue
            (0.33, (20, 80, 140)),     # Medium Blue
            (0.66, (60, 180, 200)),    # Cyan
            (1.00, (200, 240, 255)),   # Light Cyan
        ]
    },
    'monochrome': {
        'name': 'Monochrome (Dark → Light Gray)',
        'colors': [
            (0.00, (40, 40, 40)),      # Dark Gray
            (0.50, (120, 120, 120)),   # Medium Gray
            (1.00, (220, 220, 220)),   # Light Gray
        ]
    },
    'viridis': {
        'name': 'Viridis (Purple → Blue → Green → Yellow)',
        'colors': [
            (0.00, (68, 1, 84)),       # Dark Purple
            (0.25, (59, 82, 139)),     # Blue
            (0.50, (33, 144, 140)),    # Teal
            (0.75, (93, 201, 99)),     # Green
            (1.00, (253, 231, 37)),    # Yellow
        ]
    },
    'plasma': {
        'name': 'Plasma (Blue → Purple → Orange → Yellow)',
        'colors': [
            (0.00, (13, 8, 135)),      # Dark Blue
            (0.25, (126, 3, 168)),     # Purple
            (0.50, (204, 71, 120)),    # Pink
            (0.75, (248, 149, 64)),    # Orange
            (1.00, (240, 249, 33)),    # Yellow
        ]
    }
}


def get_theme_color(theme_name, ratio):
    """Get interpolated color for a given theme and ratio (0.0 to 1.0).
    
    Args:
        theme_name: Name of the theme ('default', 'fire', 'ocean', etc.)
        ratio: Heat ratio from 0.0 to 1.0
    
    Returns:
        Tuple of (r, g, b) values
    """
    theme = HEATMAP_THEMES.get(theme_name, HEATMAP_THEMES['default'])
    colors = theme['colors']
    
    # Find the two colors to interpolate between
    for i in range(len(colors) - 1):
        pos1, color1 = colors[i]
        pos2, color2 = colors[i + 1]
        
        if pos1 <= ratio <= pos2:
            # Interpolate
            t = (ratio - pos1) / (pos2 - pos1) if pos2 != pos1 else 0
            r = int(color1[0] + (color2[0] - color1[0]) * t)
            g = int(color1[1] + (color2[1] - color1[1]) * t)
            b = int(color1[2] + (color2[2] - color1[2]) * t)
            return (r, g, b)
    
    # Fallback to last color
    return colors[-1][1]

"""
Configuration management for InputTracker.
Handles persistent settings like autostart, data retention, and theme preferences.
"""

import json
import os
import sys
import winreg

# Default configuration values
DEFAULT_CONFIG = {
    'autostart': False,
    'data_retention_days': 365,  # -1 means keep forever
    'heatmap_theme': 'default',  # 'default', 'fire', 'ocean', 'monochrome'
    'minimize_to_tray': True,
    'show_notifications': True,
}

CONFIG_FILE = 'config.json'

# Registry key for Windows autostart
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "InputTracker"


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
        self._config = dict(DEFAULT_CONFIG)
        self.load()
    
    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # Merge with defaults (in case new options were added)
                    self._config.update(saved_config)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value and save."""
        self._config[key] = value
        self.save()
    
    # Property accessors for common settings
    @property
    def autostart(self):
        return self._config.get('autostart', False)
    
    @autostart.setter
    def autostart(self, value):
        self._config['autostart'] = value
        self.save()  # Save config first
        self._update_autostart_registry(value)  # Then update registry
    
    @property
    def data_retention_days(self):
        return self._config.get('data_retention_days', 365)
    
    @data_retention_days.setter
    def data_retention_days(self, value):
        self._config['data_retention_days'] = value
        self.save()
    
    @property
    def heatmap_theme(self):
        return self._config.get('heatmap_theme', 'default')
    
    @heatmap_theme.setter
    def heatmap_theme(self, value):
        self._config['heatmap_theme'] = value
        self.save()
    
    @property
    def minimize_to_tray(self):
        return self._config.get('minimize_to_tray', True)
    
    @minimize_to_tray.setter
    def minimize_to_tray(self, value):
        self._config['minimize_to_tray'] = value
        self.save()
    
    @property
    def show_notifications(self):
        return self._config.get('show_notifications', True)
    
    @show_notifications.setter
    def show_notifications(self, value):
        self._config['show_notifications'] = value
        self.save()
    
    def _get_executable_path(self):
        """Get the path to the main executable/script."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script - use pythonw to avoid console window
            python_exe = sys.executable
            # Try to use pythonw if available (no console window)
            pythonw = python_exe.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw):
                python_exe = pythonw
            
            # Get the main.py path
            main_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'main.py'
            )
            return f'"{python_exe}" "{main_script}"'
    
    def _update_autostart_registry(self, enable):
        """Update Windows registry for autostart."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                AUTOSTART_KEY,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            
            if enable:
                exe_path = self._get_executable_path()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass  # Key doesn't exist, nothing to delete
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Warning: Could not update autostart registry: {e}")
            return False
    
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

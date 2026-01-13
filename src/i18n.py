"""
Internationalization (i18n) module for ActivityTrack.
Provides multi-language support with Chinese and English translations.
"""

from typing import Dict, Optional, Callable, List
from PySide6.QtCore import QObject, Signal

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'zh': '中文'
}

# Default language
DEFAULT_LANGUAGE = 'en'

# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'en': {
        # Window titles
        'app.title': 'ActivityTrack',
        
        # Tab names
        'tab.dashboard': 'Dashboard',
        'tab.heatmap': 'Heatmap',
        'tab.applications': 'Applications',
        'tab.history': 'History',
        'tab.screen_time': 'Screen Time',
        'tab.settings': 'Settings',
        
        # Time range selector
        'time.today': 'Today',
        'time.yesterday': 'Yesterday',
        'time.week': 'Week',
        'time.month': 'Month',
        'time.year': 'Year',
        'time.all': 'All Time',
        
        # Dashboard
        'dashboard.title.today': "Today's Statistics",
        'dashboard.title.yesterday': "Yesterday's Statistics",
        'dashboard.title.week': "This Week's Statistics",
        'dashboard.title.month': "This Month's Statistics",
        'dashboard.title.year': "This Year's Statistics",
        'dashboard.title.all': "All Time Statistics",
        'dashboard.card.keystrokes': 'Keystrokes',
        'dashboard.card.clicks': 'Mouse Clicks',
        'dashboard.card.distance': 'Mouse Distance',
        'dashboard.card.scroll': 'Scroll Distance',
        'dashboard.unit.meters': 'm',
        'dashboard.unit.steps': 'steps',
        
        # Heatmap
        'heatmap.keyboard': 'Keyboard',
        'heatmap.mouse': 'Mouse',
        'heatmap.all_apps': 'All Applications',
        
        # Applications
        'apps.chart': 'Chart',
        'apps.table': 'Table',
        'apps.metric.keys': 'Keys',
        'apps.metric.clicks': 'Clicks',
        'apps.metric.scrolls': 'Scrolls',
        'apps.metric.distance': 'Distance',
        'apps.header.application': 'Application',
        'apps.header.keys': 'Keys',
        'apps.header.clicks': 'Clicks',
        'apps.header.scrolls': 'Scrolls',
        'apps.header.distance': 'Distance',
        'apps.no_data': 'No data',
        'apps.others': 'Others',
        
        # History
        'history.timeline': 'Timeline',
        'history.insights': 'Insights',
        'history.scope': 'Scope:',
        'history.all_apps': 'All Applications',
        'history.weekday': 'Weekday',
        'history.hourly': 'Hourly',
        'history.chart.today': 'Activity by Hour (Today)',
        'history.chart.history': 'Historical Activity',
        'history.chart.weekday': 'Average Activity by Day of Week',
        'history.chart.hourly': 'Average Activity by Hour of Day',
        'history.legend.keys': 'Keys',
        'history.legend.clicks': 'Clicks',
        'history.legend.avg_keys': 'Avg Keys',
        'history.legend.avg_clicks': 'Avg Clicks',
        'history.no_data': 'No Data',
        'history.weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        
        # Screen Time
        'screen_time.title': 'Screen Time',
        'screen_time.total': 'Total Screen Time',
        'screen_time.daily_avg': 'Daily Average',
        'screen_time.most_used': 'Most Used App',
        'screen_time.app_distribution': 'App Distribution',
        'screen_time.header.application': 'Application',
        'screen_time.header.time': 'Time',
        'screen_time.header.percentage': 'Percentage',
        'screen_time.no_data': 'No data',
        'screen_time.others': 'Others',
        'screen_time.idle': 'Idle',
        'screen_time.total_active': 'Active Time',
        'screen_time.total_idle': 'Idle Time',
        'screen_time.click_toggle_idle': 'Click chart to hide idle time',
        'screen_time.click_hide_idle': 'Click chart to hide idle time',
        'screen_time.click_show_idle': 'Click chart to show idle time',
        
        # Category filter
        'category.all': 'All Apps',
        'category.productivity': 'Productivity',
        'category.other': 'Other',
        
        # Settings
        'settings.title': 'Settings',
        'settings.general': 'General',
        'settings.autostart': 'Start with Windows',
        'settings.autostart_hint': '(Only available in packaged .exe version)',
        'settings.autostart_tooltip': 'Autostart is only available when running as a packaged executable (.exe)',
        'settings.minimize_tray': 'Minimize to system tray instead of closing',
        'settings.data_management': 'Data Management',
        'settings.retention': 'Keep data for:',
        'settings.retention_forever': 'Forever',
        'settings.retention_days': ' days',
        'settings.retention_hint': "Set to -1 or 'Forever' to keep all data indefinitely.",
        'settings.clear_data': 'Clear all tracking data:',
        'settings.clear_data_btn': 'Clear Data',
        'settings.appearance': 'Appearance',
        'settings.language': 'Language:',
        'settings.language_hint': 'Restart required to apply language change.',
        'settings.theme': 'Heatmap color theme:',
        'settings.preview': 'Preview:',
        'settings.idle_detection': 'Idle Detection',
        'settings.idle_timeout': 'Idle timeout:',
        'settings.idle_timeout_hint': 'Time without input before marking as idle. Set to 0 to disable.',
        'settings.idle_minutes': ' minutes',
        'settings.idle_disabled': 'Disabled',
        
        # Break reminder settings
        'settings.break_reminder': 'Break Reminder',
        'settings.break_enabled': 'Enable break reminders',
        'settings.break_interval': 'Remind after:',
        'settings.break_duration': 'Suggested break:',
        'settings.break_minutes': ' minutes',
        'settings.break_disabled': 'Disabled',
        'settings.break_hint': 'Get notified to take a break after continuous screen usage. The reminder will only trigger for genuine user activity (not automated clicks).',
        
        # Break reminder notifications
        'break_reminder.title': 'Time for a Break! 🧘',
        'break_reminder.message': "You've been using your computer for {minutes} minutes. Consider taking a {break_duration}-minute break to rest your eyes and stretch.",
        
        # App grouping
        'settings.app_grouping': 'App Grouping',
        'settings.app_grouping_desc': 'Categorize your applications into productivity and other groups for better time tracking insights.',
        'settings.manage_groups': 'Manage app groups:',
        'settings.open_grouping': 'Open Grouping',
        'settings.grouping_stats': 'Productivity: {productivity} apps | Other: {other} apps',
        
        # App grouping dialog
        'grouping.title': 'App Grouping',
        'grouping.description': 'Drag applications between lists or use the buttons to categorize them. Productivity apps are work-related, while Other includes entertainment and leisure apps.',
        'grouping.search': 'Search:',
        'grouping.search_placeholder': 'Filter apps...',
        'grouping.unassigned': 'Unassigned',
        'grouping.productivity': 'Productivity',
        'grouping.other': 'Other',
        'grouping.to_productivity': 'Productivity',
        'grouping.to_other': 'Other',
        'grouping.unassign': 'Unassign',
        'grouping.save': 'Save',
        'grouping.cancel': 'Cancel',
        'grouping.stats': 'Total: {total} apps | Productivity: {productivity} | Other: {other} | Unassigned: {unassigned}',
        
        # Theme names
        'theme.default': 'Default (Blue → Green → Yellow → Orange)',
        'theme.fire': 'Fire (Black → Red → Yellow → White)',
        'theme.ocean': 'Ocean (Deep Blue → Cyan → White)',
        'theme.monochrome': 'Monochrome (Dark → Light Gray)',
        'theme.viridis': 'Viridis (Purple → Blue → Green → Yellow)',
        'theme.plasma': 'Plasma (Blue → Purple → Orange → Yellow)',
        
        # Keyboard layout names
        'settings.keyboard_layout': 'Keyboard layout:',
        'layout.full': 'Full-size (104 keys with Numpad)',
        'layout.tkl': 'Tenkeyless / TKL (87 keys)',
        'layout.75': '75% Compact',
        'layout.60': '60% Compact',
        
        # Dialogs
        'dialog.clear_data.title': 'Clear All Data',
        'dialog.clear_data.message': "Are you sure you want to delete all tracking data?\n\nThis action cannot be undone!",
        'dialog.clear_data.confirm_title': 'Confirm Delete',
        'dialog.clear_data.confirm_message': "This will permanently delete:\n• All keystroke statistics\n• All mouse click data\n• All heatmap data\n• All application statistics\n\nAre you absolutely sure?",
        'dialog.clear_data.success_title': 'Data Cleared',
        'dialog.clear_data.success_message': 'All tracking data has been deleted successfully.',
        'dialog.clear_data.error_title': 'Error',
        'dialog.clear_data.error_message': 'Failed to clear data: {error}',
        'dialog.clear_data.warning_title': 'Warning',
        'dialog.clear_data.warning_message': 'Database not available. Cannot clear data.',
        'dialog.autostart_error.title': 'Autostart Error',
        'dialog.autostart_error.message': "Failed to update Windows startup settings:\n\n{error}\n\nThe setting has been reverted.",
        'dialog.language_change.title': 'Language Changed',
        'dialog.language_change.message': 'Please restart the application to apply the language change.',
        
        # Tray
        'tray.show': 'Show Dashboard',
        'tray.quit': 'Quit',
        'tray.tooltip': 'ActivityTrack',
        
        # Export
        'settings.export': 'Data Export',
        'settings.export_csv': 'Export to CSV files:',
        'settings.export_csv_btn': 'Export CSV',
        'settings.export_json': 'Export to JSON file:',
        'settings.export_json_btn': 'Export JSON',
        'settings.export_all': 'Export all data:',
        'settings.export_all_btn': 'Export All',
        'settings.export_range': 'Export range:',
        'dialog.export.success_title': 'Export Successful',
        'dialog.export.success_message': 'Data has been exported successfully to:\n{path}',
        'dialog.export.error_title': 'Export Error',
        'dialog.export.error_message': 'Failed to export data: {error}',
        'dialog.export.select_folder': 'Select Export Folder',
        'dialog.export.save_csv': 'Save CSV File',
        'dialog.export.save_json': 'Save JSON File',
        'dialog.export.save_image': 'Save Image File',
    },
    
    'zh': {
        # Window titles
        'app.title': 'ActivityTrack',
        
        # Tab names
        'tab.dashboard': '仪表盘',
        'tab.heatmap': '热力图',
        'tab.applications': '应用程序',
        'tab.history': '历史记录',
        'tab.screen_time': '屏幕时间',
        'tab.settings': '设置',
        
        # Time range selector
        'time.today': '今天',
        'time.yesterday': '昨天',
        'time.week': '本周',
        'time.month': '本月',
        'time.year': '今年',
        'time.all': '全部时间',
        
        # Dashboard
        'dashboard.title.today': "今日统计",
        'dashboard.title.yesterday': "昨日统计",
        'dashboard.title.week': "本周统计",
        'dashboard.title.month': "本月统计",
        'dashboard.title.year': "今年统计",
        'dashboard.title.all': "全部统计",
        'dashboard.card.keystrokes': '按键次数',
        'dashboard.card.clicks': '鼠标点击',
        'dashboard.card.distance': '鼠标移动距离',
        'dashboard.card.scroll': '滚轮滚动',
        'dashboard.unit.meters': '米',
        'dashboard.unit.steps': '格',
        
        # Heatmap
        'heatmap.keyboard': '键盘',
        'heatmap.mouse': '鼠标',
        'heatmap.all_apps': '所有应用程序',
        
        # Applications
        'apps.chart': '图表',
        'apps.table': '表格',
        'apps.metric.keys': '按键',
        'apps.metric.clicks': '点击',
        'apps.metric.scrolls': '滚动',
        'apps.metric.distance': '距离',
        'apps.header.application': '应用程序',
        'apps.header.keys': '按键',
        'apps.header.clicks': '点击',
        'apps.header.scrolls': '滚动',
        'apps.header.distance': '距离',
        'apps.no_data': '暂无数据',
        'apps.others': '其他',
        
        # History
        'history.timeline': '时间线',
        'history.insights': '统计分析',
        'history.scope': '范围：',
        'history.all_apps': '所有应用程序',
        'history.weekday': '星期',
        'history.hourly': '小时',
        'history.chart.today': '今日活动（按小时）',
        'history.chart.history': '历史活动',
        'history.chart.weekday': '按星期平均活动',
        'history.chart.hourly': '按小时平均活动',
        'history.legend.keys': '按键',
        'history.legend.clicks': '点击',
        'history.legend.avg_keys': '平均按键',
        'history.legend.avg_clicks': '平均点击',
        'history.no_data': '暂无数据',
        'history.weekdays': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        
        # Screen Time
        'screen_time.title': '屏幕时间',
        'screen_time.total': '总屏幕时间',
        'screen_time.daily_avg': '日均使用',
        'screen_time.most_used': '最常用应用',
        'screen_time.app_distribution': '应用分布',
        'screen_time.header.application': '应用程序',
        'screen_time.header.time': '时间',
        'screen_time.header.percentage': '百分比',
        'screen_time.no_data': '暂无数据',
        'screen_time.others': '其他',
        'screen_time.idle': '空闲',
        'screen_time.total_active': '活跃时间',
        'screen_time.total_idle': '空闲时间',
        'screen_time.click_toggle_idle': '点击图表隐藏空闲时间',
        'screen_time.click_hide_idle': '点击图表隐藏空闲时间',
        'screen_time.click_show_idle': '点击图表显示空闲时间',
        
        # Category filter
        'category.all': '全部应用',
        'category.productivity': '生产力',
        'category.other': '其他',
        
        # Settings
        'settings.title': '设置',
        'settings.general': '常规',
        'settings.autostart': '开机自启动',
        'settings.autostart_hint': '（仅在打包版本中可用）',
        'settings.autostart_tooltip': '自启动功能仅在打包为可执行文件（.exe）后可用',
        'settings.minimize_tray': '关闭时最小化到系统托盘',
        'settings.data_management': '数据管理',
        'settings.retention': '数据保留：',
        'settings.retention_forever': '永久',
        'settings.retention_days': ' 天',
        'settings.retention_hint': '设置为 -1 或"永久"以无限期保留所有数据。',
        'settings.clear_data': '清除所有追踪数据：',
        'settings.clear_data_btn': '清除数据',
        'settings.appearance': '外观',
        'settings.language': '语言：',
        'settings.language_hint': '更改语言后需要重启应用。',
        'settings.theme': '热力图配色主题：',
        'settings.preview': '预览：',
        'settings.idle_detection': '空闲检测',
        'settings.idle_timeout': '空闲超时：',
        'settings.idle_timeout_hint': '无输入多长时间后标记为空闲。设为 0 禁用此功能。',
        'settings.idle_minutes': ' 分钟',
        'settings.idle_disabled': '已禁用',
        
        # Break reminder settings
        'settings.break_reminder': '久坐提醒',
        'settings.break_enabled': '启用久坐提醒',
        'settings.break_interval': '提醒间隔：',
        'settings.break_duration': '建议休息：',
        'settings.break_minutes': ' 分钟',
        'settings.break_disabled': '已禁用',
        'settings.break_hint': '在持续使用电脑一段时间后收到休息提醒。提醒只会在检测到真实用户活动时触发（不会被自动化程序触发）。',
        
        # Break reminder notifications
        'break_reminder.title': '该休息一下了！🧘',
        'break_reminder.message': '您已连续使用电脑 {minutes} 分钟。建议休息 {break_duration} 分钟，让眼睛休息一下，活动活动身体。',
        
        # App grouping
        'settings.app_grouping': '应用分组',
        'settings.app_grouping_desc': '将应用程序分类为生产力和其他类别，以获得更好的时间追踪洞察。',
        'settings.manage_groups': '管理应用分组：',
        'settings.open_grouping': '打开分组',
        'settings.grouping_stats': '生产力：{productivity} 个应用 | 其他：{other} 个应用',
        
        # App grouping dialog
        'grouping.title': '应用分组',
        'grouping.description': '使用按钮将应用程序分类到不同组别。生产力应用包括工作相关的软件，其他则包括娱乐和休闲应用。',
        'grouping.search': '搜索：',
        'grouping.search_placeholder': '筛选应用...',
        'grouping.unassigned': '未分组',
        'grouping.productivity': '生产力',
        'grouping.other': '其他',
        'grouping.to_productivity': '生产力',
        'grouping.to_other': '其他',
        'grouping.unassign': '取消分组',
        'grouping.save': '保存',
        'grouping.cancel': '取消',
        'grouping.stats': '总计：{total} 个应用 | 生产力：{productivity} | 其他：{other} | 未分组：{unassigned}',
        
        # Theme names
        'theme.default': '默认（蓝 → 绿 → 黄 → 橙）',
        'theme.fire': '火焰（黑 → 红 → 黄 → 白）',
        'theme.ocean': '海洋（深蓝 → 青 → 白）',
        'theme.monochrome': '单色（深灰 → 浅灰）',
        'theme.viridis': 'Viridis（紫 → 蓝 → 绿 → 黄）',
        'theme.plasma': 'Plasma（蓝 → 紫 → 橙 → 黄）',
        
        # Keyboard layout names
        'settings.keyboard_layout': '键盘布局：',
        'layout.full': '全尺寸（104键，含数字键盘）',
        'layout.tkl': '无数字键盘 / TKL（87键）',
        'layout.75': '75% 紧凑布局',
        'layout.60': '60% 紧凑布局',
        
        # Dialogs
        'dialog.clear_data.title': '清除所有数据',
        'dialog.clear_data.message': '确定要删除所有追踪数据吗？\n\n此操作无法撤销！',
        'dialog.clear_data.confirm_title': '确认删除',
        'dialog.clear_data.confirm_message': '这将永久删除：\n• 所有按键统计\n• 所有鼠标点击数据\n• 所有热力图数据\n• 所有应用程序统计\n\n确定要继续吗？',
        'dialog.clear_data.success_title': '数据已清除',
        'dialog.clear_data.success_message': '所有追踪数据已成功删除。',
        'dialog.clear_data.error_title': '错误',
        'dialog.clear_data.error_message': '清除数据失败：{error}',
        'dialog.clear_data.warning_title': '警告',
        'dialog.clear_data.warning_message': '数据库不可用，无法清除数据。',
        'dialog.autostart_error.title': '自启动错误',
        'dialog.autostart_error.message': '更新 Windows 启动设置失败：\n\n{error}\n\n设置已恢复。',
        'dialog.language_change.title': '语言已更改',
        'dialog.language_change.message': '请重启应用以应用语言更改。',
        
        # Tray
        'tray.show': '显示主界面',
        'tray.quit': '退出',
        'tray.tooltip': 'ActivityTrack',
        
        # Export
        'settings.export': '数据导出',
        'settings.export_csv': '导出为 CSV 文件：',
        'settings.export_csv_btn': '导出 CSV',
        'settings.export_json': '导出为 JSON 文件：',
        'settings.export_json_btn': '导出 JSON',
        'settings.export_all': '导出所有数据：',
        'settings.export_all_btn': '全部导出',
        'settings.export_range': '导出范围：',
        'dialog.export.success_title': '导出成功',
        'dialog.export.success_message': '数据已成功导出到：\n{path}',
        'dialog.export.error_title': '导出错误',
        'dialog.export.error_message': '导出数据失败：{error}',
        'dialog.export.select_folder': '选择导出文件夹',
        'dialog.export.save_csv': '保存 CSV 文件',
        'dialog.export.save_json': '保存 JSON 文件',
        'dialog.export.save_image': '保存图片文件',
    }
}


class I18n(QObject):
    """Internationalization manager singleton."""
    
    # Signal emitted when language changes
    language_changed = Signal(str)
    
    _instance: Optional['I18n'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self._initialized = True
        self._current_language = DEFAULT_LANGUAGE
        self._callbacks: List[Callable] = []
    
    @property
    def current_language(self) -> str:
        return self._current_language
    
    @current_language.setter
    def current_language(self, lang: str):
        if lang in SUPPORTED_LANGUAGES and lang != self._current_language:
            self._current_language = lang
            self.language_changed.emit(lang)
            self._notify_callbacks()
    
    def get(self, key: str, **kwargs) -> str:
        """Get translated string for the given key.
        
        Args:
            key: Translation key (e.g., 'tab.dashboard')
            **kwargs: Format arguments for string interpolation
            
        Returns:
            Translated string, or key if not found
        """
        translations = TRANSLATIONS.get(self._current_language, TRANSLATIONS[DEFAULT_LANGUAGE])
        text = translations.get(key)
        
        if text is None:
            # Fallback to English
            text = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
        
        # Handle format arguments
        if kwargs and isinstance(text, str):
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return text
    
    def get_list(self, key: str) -> List[str]:
        """Get translated list for the given key.
        
        Args:
            key: Translation key that maps to a list
            
        Returns:
            Translated list, or empty list if not found
        """
        translations = TRANSLATIONS.get(self._current_language, TRANSLATIONS[DEFAULT_LANGUAGE])
        result = translations.get(key)
        
        if result is None:
            result = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, [])
        
        return result if isinstance(result, list) else []
    
    def register_callback(self, callback: Callable):
        """Register a callback to be called when language changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister a language change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks of language change."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in i18n callback: {e}")


# Global instance
_i18n = I18n()


def tr(key: str, **kwargs) -> str:
    """Convenience function to get translated string.
    
    Args:
        key: Translation key
        **kwargs: Format arguments
        
    Returns:
        Translated string
    """
    return _i18n.get(key, **kwargs)


def tr_list(key: str) -> List[str]:
    """Convenience function to get translated list.
    
    Args:
        key: Translation key
        
    Returns:
        Translated list
    """
    return _i18n.get_list(key)


def get_i18n() -> I18n:
    """Get the global I18n instance."""
    return _i18n


def set_language(lang: str):
    """Set the current language.
    
    Args:
        lang: Language code ('en' or 'zh')
    """
    _i18n.current_language = lang


def get_language() -> str:
    """Get the current language code."""
    return _i18n.current_language


def get_supported_languages() -> Dict[str, str]:
    """Get dictionary of supported languages."""
    return SUPPORTED_LANGUAGES.copy()

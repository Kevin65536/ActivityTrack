"""Portable paths, single-instance ownership, and orderly application shutdown."""
import logging
import os
from pathlib import Path
import sys

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox


def resolve_data_dir(explicit=None):
    override = explicit or os.environ.get('ACTIVITYTRACK_DATA_DIR')
    if override:
        return Path(override).expanduser().resolve()
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    if not getattr(sys, 'frozen', False) or any((base / name).exists() for name in ('portable.txt', 'tracker.db', 'config.json')):
        return base
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ActivityTrack'


class NotificationBridge(QObject):
    requested = Signal(str, str)

    def __init__(self, tray, config):
        super().__init__()
        self.tray = tray
        self.config = config
        self.requested.connect(self.show_notification)

    @Slot(str, str)
    def show_notification(self, title, message):
        if self.config.show_notifications:
            self.tray.showMessage(title, message, self.tray.MessageIcon.Information, 10000)


class ShutdownController:
    def __init__(self, app, tracker, reminder, window, tray, session_events):
        self.app, self.tracker, self.reminder = app, tracker, reminder
        self.window, self.tray, self.session_events = window, tray, session_events
        self.finished = False
        self.busy = False

    def shutdown(self, *, show_error=True):
        if self.finished:
            return True
        if self.busy:
            return False
        self.busy = True
        try:
            self.reminder.stop()
            self.tracker.stop()
        except Exception as error:
            logging.getLogger(__name__).exception('Shutdown failed; pending data remains in memory')
            if show_error:
                title = '保存失败' if self.window.config.language == 'zh' else 'Could not save activity'
                message = ('请保持程序运行，解决磁盘或权限问题后再次退出。\n' if self.window.config.language == 'zh'
                           else 'Keep the app open, resolve the disk or permission error, and retry Exit.\n')
                QMessageBox.critical(self.window, title, message + str(error))
            return False
        finally:
            self.busy = False
        self.window.timer.stop()
        self.session_events.close()
        self.tray.hide()
        self.finished = True
        return True

    def quit(self):
        if self.shutdown():
            self.app.quit()

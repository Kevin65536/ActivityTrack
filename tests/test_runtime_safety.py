import ctypes
from ctypes import wintypes
import datetime
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QLockFile
from src.runtime import ShutdownController, resolve_data_dir
from src.session_events import SessionEvents, WM_WTSSESSION_CHANGE, WM_POWERBROADCAST
from src.tracker import ActivityTrack, CapturedEvent
from src.ui.main_window import MainWindow
from src.ui.settings import SettingsWidget
from src.ui.recording_status import coherent_refresh, health_message


class RuntimeSafetyTests(unittest.TestCase):
    def test_close_routes_to_save_controller(self):
        window = SimpleNamespace(config=SimpleNamespace(minimize_to_tray=False), quit_requested=Mock())
        event = Mock()
        MainWindow.closeEvent(window, event)
        event.ignore.assert_called_once()
        window.quit_requested.emit.assert_called_once()

    def test_failed_shutdown_keeps_app_open_and_can_retry(self):
        app, tracker, reminder, window, tray, sessions = (Mock() for _ in range(6))
        tracker.stop.side_effect = [OSError('disk full'), None]
        control = ShutdownController(app, tracker, reminder, window, tray, sessions)
        with patch('src.runtime.QMessageBox.critical'), self.assertLogs('src.runtime', level='ERROR'):
            control.quit()
        app.quit.assert_not_called()
        tray.hide.assert_not_called()
        self.assertFalse(control.finished)
        control.quit()
        app.quit.assert_called_once()
        sessions.close.assert_called_once()
        self.assertTrue(control.finished)
        control.shutdown()
        self.assertEqual(tracker.stop.call_count, 2)

    def test_windows_messages_preserve_overlapping_pause_reasons(self):
        tracker = Mock()
        events = SessionEvents(tracker)
        events.hwnd = 123
        msg = wintypes.MSG()
        msg.hWnd, msg.message, msg.wParam = 123, WM_WTSSESSION_CHANGE, 7
        self.assertEqual(events.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(msg)), (False, 0))
        events.handle_message(WM_POWERBROADCAST, 4)
        events.handle_message(WM_POWERBROADCAST, 18)
        events.handle_message(WM_WTSSESSION_CHANGE, 8)
        self.assertEqual([call.args for call in tracker.notify_session_state.call_args_list],
                         [(True, 'lock'), (True, 'suspend'), (False, 'suspend'), (False, 'lock')])

    def test_settings_clear_cannot_reinsert_pending_activity(self):
        with tempfile.TemporaryDirectory() as directory:
            tracker = ActivityTrack(str(Path(directory) / 'test.db'))
            self.addCleanup(tracker.stop)
            tracker.on_press(65, 30, app_name='private.exe')
            tracker._metadata_pending['private.exe'] = ('Private', 'private-path')
            widget = SimpleNamespace(tracker=tracker, database=tracker.db, settings_changed=Mock())
            with patch('src.ui.settings.QMessageBox.information'):
                SettingsWidget.clear_all_data(widget)
            tracker.flush_stats()
            self.assertEqual(tracker.db.get_all_time_stats()[0], None)
            self.assertEqual(tracker.db.get_app_metadata_dict(), {})
            tracker.stop()

    def test_retention_discards_old_queue_events_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            tracker = ActivityTrack(str(Path(directory) / 'test.db'))
            old = datetime.datetime.now() - datetime.timedelta(days=10)
            tracker._metadata_pending['old.exe'] = ('Old', 'private-path')
            tracker.set_retention_days(1)
            with patch.object(tracker, 'get_active_app_name', return_value='old.exe') as lookup:
                tracker._process_event(CapturedEvent('key', old.timestamp(), 1, (65, 30), 1, 0))
                lookup.assert_not_called()
            tracker.flush_stats()
            self.assertEqual(tracker.db.get_app_metadata_dict(), {})
            tracker.stop()

    def test_busy_ui_refresh_skips_frame(self):
        lock = threading.RLock()
        entered, release = threading.Event(), threading.Event()
        def hold_lock():
            with lock:
                entered.set()
                release.wait(2)
        worker = threading.Thread(target=hold_lock)
        worker.start()
        entered.wait(2)
        method = Mock()
        try:
            coherent_refresh(method)(SimpleNamespace(tracker=SimpleNamespace(lock=lock)))
            method.assert_not_called()
        finally:
            release.set()
            worker.join()

    def test_lock_prevents_second_recorder_for_same_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (QLockFile(str(Path(directory) / 'activitytrack.lock')) for _ in range(2))
            first.setStaleLockTime(0)
            second.setStaleLockTime(0)
            self.assertTrue(first.tryLock(0))
            self.assertFalse(second.tryLock(0))
            first.unlock()
            self.assertTrue(second.tryLock(0))
            second.unlock()

    def test_explicit_directory_and_error_status(self):
        self.assertEqual(resolve_data_dir('test-data'), Path('test-data').resolve())
        message, warning = health_message({'write_error': 'disk full'}, True)
        self.assertTrue(warning)
        self.assertIn('保存失败', message)

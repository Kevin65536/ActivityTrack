import ctypes
import datetime
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.native_input import (
    NativeInputCapture, KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT,
    WM_KEYDOWN, WM_KEYUP, WM_LBUTTONDOWN,
)
from src.tracker import ActivityTrack, CapturedEvent


class RecordingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'test.db')
        with patch.object(ActivityTrack, '_init_screen_metrics'):
            self.tracker = ActivityTrack(self.path)
        self.tracker.px_per_mm = 96 / 25.4
        self.tracker.get_active_app_name = lambda *args: 'fixture.exe'
        self.addCleanup(self.tracker.db.close)
        self.t0 = datetime.datetime(2026, 10, 25, 10).timestamp()

    def initialize_clock(self):
        self.tracker.current_foreground_app = 'fixture.exe'
        self.tracker.foreground_app_start_time = self.t0
        self.tracker.last_activity_time = self.t0
        self.tracker._last_wall_time_observed = self.t0
        self.tracker._last_monotonic_time_observed = 100.0

    def tick(self, seconds):
        with patch('src.tracker.time.time', return_value=self.t0 + seconds), patch('src.tracker.time.monotonic', return_value=100 + seconds):
            self.tracker._check_foreground_window()
            if seconds % 5 == 0:
                self.tracker._record_foreground_time()
                self.tracker.flush_stats()

    def saved_times(self):
        with self.tracker.db.read_connection() as conn:
            return dict(conn.execute('SELECT app_name, SUM(duration_seconds) FROM app_foreground_time GROUP BY app_name'))

    def test_idle_transition_never_counts_an_interval_twice(self):
        self.initialize_clock()
        for second in range(1, 311):
            self.tick(second)
        self.assertEqual(self.saved_times(), {'[Idle]': 10.0, 'fixture.exe': 300.0})
        self.assertTrue(self.tracker.is_idle)

    def test_input_after_sleep_does_not_record_suspended_idle_time(self):
        self.initialize_clock()
        self.tracker.is_idle = True
        self.tracker.idle_start_time = self.t0
        self.tracker.foreground_app_start_time = None
        self.tracker.last_activity_time = self.t0 - 600
        self.tracker.on_press(65, 30, timestamp=self.t0 + 7200, monotonic_time=7300, app_name='fixture.exe')
        self.tracker.flush_stats()
        self.assertEqual(sum(self.saved_times().values()), 0)
        self.assertFalse(self.tracker.is_idle)

    def test_fractional_seconds_survive_repeated_flushes(self):
        for index in range(20):
            self.tracker._add_foreground_duration('fixture.exe', self.t0 + index * 5.9, self.t0 + (index + 1) * 5.9)
            self.tracker.flush_stats()
        self.assertAlmostEqual(self.saved_times()['fixture.exe'], 118.0, places=5)

    def test_locked_session_stays_paused_across_suspend_resume(self):
        self.initialize_clock()
        self.tracker._handle_session_state(True, 'lock', now=self.t0 + 5, monotonic_time=105)
        self.tracker._handle_session_state(True, 'suspend', now=self.t0 + 6, monotonic_time=106)
        self.tracker._handle_session_state(False, 'suspend', now=self.t0 + 3606, monotonic_time=3706)
        self.tracker.on_press(65, 30, timestamp=self.t0 + 3610, monotonic_time=3710)
        self.assertFalse(self.tracker.hourly_input_buffer)
        self.tracker._handle_session_state(False, 'lock', now=self.t0 + 3615, monotonic_time=3715)
        self.tracker.on_press(65, 30, timestamp=self.t0 + 3616, monotonic_time=3716)
        self.tracker._record_foreground_time(self.t0 + 3620, 3720)
        self.tracker.flush_stats()
        self.assertEqual(self.saved_times(), {'fixture.exe': 9.0})

    def test_clock_rollback_resets_baseline_without_negative_duration(self):
        self.initialize_clock()
        self.tracker._record_foreground_time(self.t0 + 5, 105)
        self.tracker._record_foreground_time(self.t0 - 3600, 106)
        self.tracker._record_foreground_time(self.t0 - 3595, 111)
        self.tracker.flush_stats()
        self.assertEqual(sum(self.saved_times().values()), 10)

    def test_event_uses_capture_date_when_processing_crosses_midnight(self):
        before = datetime.datetime(2026, 10, 24, 23, 59, 59).timestamp()
        for wall, mono in ((before, 100), (before + 2, 102)):
            event = CapturedEvent('key', wall, mono, (65, 30), 0, 0)
            self.tracker._process_event(event)
        self.tracker.flush_stats()
        with self.tracker.db.read_connection() as conn:
            self.assertEqual(conn.execute('SELECT date, key_count FROM daily_stats ORDER BY date').fetchall(),
                             [('2026-10-24', 1), ('2026-10-25', 1)])

    def test_queue_overflow_is_bounded_and_reported(self):
        self.tracker._queue_limit = 1
        self.assertTrue(self.tracker._enqueue_event('key', (65, 30), 0))
        self.assertFalse(self.tracker._enqueue_event('key', (65, 30), 0))
        self.assertTrue(self.tracker._enqueue_event('session', (True, 'lock')))
        health = self.tracker.get_health_snapshot()
        self.assertEqual(health['dropped_events'], 1)
        self.assertEqual(health['queue_depth'], 2)

    def test_hook_returns_even_when_recorder_lock_is_held(self):
        keyboard = KBDLLHOOKSTRUCT(vkCode=65, scanCode=30)
        finished = threading.Event()

        def callback():
            self.tracker.low_level_keyboard_proc(0, WM_KEYDOWN, ctypes.addressof(keyboard))
            finished.set()

        with patch('src.native_input.user32.CallNextHookEx', return_value=0), patch('src.native_input.user32.GetForegroundWindow', return_value=0):
            with self.tracker.lock:
                thread = threading.Thread(target=callback)
                thread.start()
                fast = finished.wait(0.5)
            thread.join(2)
        self.assertTrue(fast, 'callback must never wait for database/recorder locks')
        self.assertEqual(self.tracker._events.qsize(), 1)

    def test_shutdown_drains_queue_before_closing_database(self):
        self.tracker.start(install_hooks=False)
        for _ in range(100):
            self.tracker._enqueue_event('key', (65, 30), 0)
        self.tracker.stop()
        self.assertFalse(self.tracker.worker_thread.is_alive())
        self.assertTrue(self.tracker.db._closed)
        conn = sqlite3.connect(self.path)
        try:
            self.assertEqual(conn.execute('SELECT SUM(key_count) FROM daily_stats').fetchone()[0], 100)
        finally:
            conn.close()
        self.tracker.stop()  # idempotent

    def test_failed_shutdown_can_retry_without_losing_buffer(self):
        with self.tracker.db.transaction() as conn:
            conn.execute("CREATE TRIGGER fail_final BEFORE INSERT ON daily_stats "
                         "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        self.tracker.start(install_hooks=False)
        self.tracker._enqueue_event('key', (65, 30), 0)
        with self.assertLogs('src.tracker', level='ERROR'):
            with self.assertRaisesRegex(RuntimeError, 'pending activity'):
                self.tracker.stop()
        self.assertFalse(self.tracker.db._closed)
        with self.tracker.db.transaction() as conn:
            conn.execute('DROP TRIGGER fail_final')
        self.tracker.stop()
        conn = sqlite3.connect(self.path)
        try:
            self.assertEqual(conn.execute('SELECT SUM(key_count) FROM daily_stats').fetchone()[0], 1)
        finally:
            conn.close()

    def test_clear_invalidates_old_queue_and_buffers(self):
        self.tracker.on_press(65, 30)
        self.tracker._enqueue_event('key', (65, 30), 0)
        self.tracker.clear_all_data()
        self.tracker._enqueue_event('key', (65, 30), 0)
        while not self.tracker._events.empty():
            self.tracker._process_event(self.tracker._events.get_nowait())
        self.tracker.flush_stats()
        self.assertEqual(self.tracker.db.get_today_stats()[1], 1)

    def test_scroll_units_match_global_and_application_statistics(self):
        self.tracker.on_scroll(420)
        self.tracker.flush_stats()
        self.assertEqual(self.tracker.db.get_today_stats()[4], 3.5)
        self.assertEqual(self.tracker.db.get_app_stats_summary()[0][3], 3.5)


class NativeCallbackTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.capture = NativeInputCapture(lambda *event: self.events.append(event))
        self.next_hook = patch('src.native_input.user32.CallNextHookEx', return_value=0)
        self.foreground = patch('src.native_input.user32.GetForegroundWindow', return_value=0)
        self.next_hook.start()
        self.foreground.start()
        self.addCleanup(self.next_hook.stop)
        self.addCleanup(self.foreground.stop)

    def test_injected_keys_do_not_poison_held_key_state(self):
        keyboard = KBDLLHOOKSTRUCT(vkCode=65, scanCode=30, flags=0x10)
        self.capture.keyboard_proc(0, WM_KEYDOWN, ctypes.addressof(keyboard))
        self.assertFalse(self.capture.keys_held)
        keyboard.flags = 0
        self.capture.keyboard_proc(0, WM_KEYDOWN, ctypes.addressof(keyboard))
        self.capture.keyboard_proc(0, WM_KEYDOWN, ctypes.addressof(keyboard))
        self.assertEqual(len(self.events), 1)
        self.capture.keyboard_proc(0, WM_KEYUP, ctypes.addressof(keyboard))
        self.capture.keyboard_proc(0, WM_KEYDOWN, ctypes.addressof(keyboard))
        self.assertEqual(len(self.events), 2)

    def test_injected_mouse_input_is_not_recorded(self):
        mouse = MSLLHOOKSTRUCT(flags=1)
        self.capture.mouse_proc(0, WM_LBUTTONDOWN, ctypes.addressof(mouse))
        self.assertFalse(self.events)
        mouse.flags = 0
        self.capture.mouse_proc(0, WM_LBUTTONDOWN, ctypes.addressof(mouse))
        self.assertEqual(len(self.events), 1)

    def test_partial_hook_install_failure_unhooks_the_successful_hook(self):
        with patch('src.native_input.user32.PeekMessageW'), patch('src.native_input.user32.SetWindowsHookExW', side_effect=[123, 0]), patch('src.native_input.user32.UnhookWindowsHookEx') as unhook:
            self.capture._run()
        unhook.assert_called_once_with(123)
        self.assertIsNotNone(self.capture.last_error)
        self.assertTrue(self.capture.ready.is_set())


if __name__ == '__main__':
    unittest.main()

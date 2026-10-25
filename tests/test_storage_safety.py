import datetime
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.database import Database
from src.exporter import DataExporter
from src.tracker import ActivityTrack


class StorageSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        with patch.object(ActivityTrack, '_init_screen_metrics'):
            self.tracker = ActivityTrack(str(Path(self.directory.name) / 'test.db'))
        self.db = self.tracker.db
        self.addCleanup(self.db.close)
        self.tracker.get_active_app_name = lambda: 'fixture.exe'
        self.today = datetime.date.today()

    def value(self, query):
        with self.db.read_connection() as conn:
            return conn.execute(query).fetchone()[0]

    def test_failed_batch_rolls_back_every_table_and_can_retry(self):
        self.tracker.on_press(65, 30)
        with self.db.transaction() as conn:
            conn.execute("CREATE TRIGGER fail_batch BEFORE INSERT ON heatmap_data "
                         "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.tracker.flush_stats()
        for table in ('daily_stats', 'app_stats', 'hourly_app_stats'):
            self.assertEqual(self.value(f'SELECT COUNT(*) FROM {table}'), 0)
        self.assertTrue(self.tracker.hourly_input_buffer)
        with self.db.transaction() as conn:
            conn.execute('DROP TRIGGER fail_batch')
        self.tracker.flush_stats()
        for table in ('daily_stats', 'app_stats', 'hourly_app_stats'):
            self.assertEqual(self.value(f'SELECT SUM(key_count) FROM {table}'), 1)
        self.assertFalse(self.tracker.hourly_input_buffer)

    def test_foreground_failure_does_not_discard_input_buffers(self):
        self.tracker.on_press(65, 30)
        self.tracker.foreground_time_buffer[(self.today, 10, 'fixture.exe')] = 5.9
        with self.db.transaction() as conn:
            conn.execute("CREATE TRIGGER fail_time BEFORE INSERT ON app_foreground_time "
                         "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.tracker.flush_stats()
        self.assertEqual(self.value('SELECT COUNT(*) FROM daily_stats'), 0)
        self.assertTrue(self.tracker.hourly_input_buffer)
        with self.db.transaction() as conn:
            conn.execute('DROP TRIGGER fail_time')
        self.tracker.flush_stats()
        self.assertEqual(self.value('SELECT SUM(key_count) FROM daily_stats'), 1)
        self.assertAlmostEqual(self.value('SELECT SUM(duration_seconds) FROM app_foreground_time'), 5.9)

    def test_failed_export_cannot_rollback_concurrent_writer(self):
        finished = threading.Event()
        results = []

        def export():
            try:
                results.append(DataExporter(self.db).export_daily_stats_csv(
                    str(Path(self.directory.name) / 'missing' / 'export.csv')))
            finally:
                finished.set()

        with self.db.transaction():
            self.db.update_stats(self.today, key_count=1)
            thread = threading.Thread(target=export)
            thread.start()
            self.assertTrue(finished.wait(2), 'read-only export must not wait for the writer lock')
        thread.join(2)
        self.assertEqual(results, [False])
        self.assertEqual(self.value('SELECT SUM(key_count) FROM daily_stats'), 1)

    def test_read_snapshot_is_consistent_across_writes(self):
        with self.db.read_connection() as reader:
            self.assertEqual(reader.execute('SELECT COUNT(*) FROM daily_stats').fetchone()[0], 0)
            self.db.update_stats(self.today, key_count=1)
            self.assertEqual(reader.execute('SELECT COUNT(*) FROM daily_stats').fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                reader.execute('DELETE FROM daily_stats')
        self.assertEqual(self.value('SELECT SUM(key_count) FROM daily_stats'), 1)

    def test_caught_nested_failure_still_aborts_outer_transaction(self):
        with self.assertRaisesRegex(RuntimeError, 'nested database update failed'):
            with self.db.transaction():
                self.db.update_stats(self.today, key_count=1)
                try:
                    with self.db.transaction():
                        raise ValueError('synthetic failure')
                except ValueError:
                    pass
        self.assertEqual(self.value('SELECT COUNT(*) FROM daily_stats'), 0)

    def test_closed_database_cannot_be_reopened_by_a_late_worker(self):
        self.db.close()
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            self.db.update_stats(self.today, key_count=1)
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            with self.db.read_connection():
                pass

    def seed_every_table(self, date, app):
        self.db.update_stats(date, key_count=1)
        self.db.update_app_stats(date, app, key_count=1)
        self.db.update_hourly_app_stats(date, 10, app, key_count=1)
        self.db.update_heatmap(date, 30, 1)
        self.db.update_mouse_heatmap(date, 0, 0, 1)
        self.db.update_app_heatmap(date, app, 30, 1)
        self.db.update_app_mouse_heatmap(date, app, 0, 0, 1)
        self.db.update_foreground_time(date, 10, app, 0.5)
        self.db.update_app_metadata(app, 'Fixture', r'C:\Fixture\fixture.exe')

    def test_clear_removes_all_statistics_and_paths(self):
        self.seed_every_table(self.today, 'fixture.exe')
        self.db.clear_all_data()
        for table in self.db._dated_tables() + ('app_metadata',):
            self.assertEqual(self.value(f'SELECT COUNT(*) FROM {table}'), 0)

    def test_retention_removes_old_rows_and_orphan_metadata_only(self):
        old = self.today - datetime.timedelta(days=800)
        self.seed_every_table(old, 'old.exe')
        self.seed_every_table(self.today, 'current.exe')
        self.db.prune_before(self.today - datetime.timedelta(days=6))
        for table in self.db._dated_tables():
            self.assertEqual(self.value(f'SELECT COUNT(*) FROM {table}'), 1)
        self.assertEqual(set(self.db.get_app_metadata_dict()), {'current.exe'})


class SchemaCompatibilityTests(unittest.TestCase):
    def test_legacy_app_schema_is_migrated_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'legacy.db')
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute('CREATE TABLE app_stats (date DATE, app_name TEXT, key_count INTEGER, PRIMARY KEY(date, app_name))')
                conn.execute("INSERT INTO app_stats VALUES ('2026-10-01', 'old.exe', 12)")
            db = Database(path)
            try:
                rows = db.get_app_stats_summary()
                self.assertEqual(rows, [('old.exe', 12, 0, 0, 0)])
                db.update_foreground_time(datetime.date(2026, 10, 1), 10, 'old.exe', 1.25)
                self.assertEqual(db.get_total_foreground_time('2026-10-01', '2026-10-01'), 1.25)
            finally:
                db.close()

    def test_in_memory_database_exports_a_snapshot(self):
        db = Database(':memory:')
        try:
            db.update_stats(datetime.date.today(), key_count=3)
            with db.read_connection() as conn:
                self.assertEqual(conn.execute('SELECT SUM(key_count) FROM daily_stats').fetchone()[0], 3)
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()

import unittest
import datetime
import os
import tempfile

from src.screen_time import split_interval_by_local_hour
from src.tracker import ActivityTrack


class TestScreenTimeBucketing(unittest.TestCase):
    def test_split_within_one_hour(self):
        start = datetime.datetime(2025, 12, 24, 10, 0, 0).timestamp()
        end = datetime.datetime(2025, 12, 24, 10, 30, 0).timestamp()
        parts = split_interval_by_local_hour(start, end)
        self.assertEqual(len(parts), 1)
        day, hour, seconds = parts[0]
        self.assertEqual(day, datetime.date(2025, 12, 24))
        self.assertEqual(hour, 10)
        self.assertAlmostEqual(seconds, 1800.0, places=6)

    def test_split_cross_hour(self):
        start = datetime.datetime(2025, 12, 24, 0, 30, 0).timestamp()
        end = datetime.datetime(2025, 12, 24, 1, 15, 0).timestamp()
        parts = split_interval_by_local_hour(start, end)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0][0], datetime.date(2025, 12, 24))
        self.assertEqual(parts[0][1], 0)
        self.assertAlmostEqual(parts[0][2], 1800.0, places=6)
        self.assertEqual(parts[1][0], datetime.date(2025, 12, 24))
        self.assertEqual(parts[1][1], 1)
        self.assertAlmostEqual(parts[1][2], 900.0, places=6)

    def test_split_cross_midnight(self):
        start = datetime.datetime(2025, 12, 24, 23, 59, 30).timestamp()
        end = datetime.datetime(2025, 12, 25, 0, 0, 30).timestamp()
        parts = split_interval_by_local_hour(start, end)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0][0], datetime.date(2025, 12, 24))
        self.assertEqual(parts[0][1], 23)
        self.assertAlmostEqual(parts[0][2], 30.0, places=6)
        self.assertEqual(parts[1][0], datetime.date(2025, 12, 25))
        self.assertEqual(parts[1][1], 0)
        self.assertAlmostEqual(parts[1][2], 30.0, places=6)

    def test_no_single_hour_exceeds_3600(self):
        # Simulate a 3-hour interval that would previously be dumped into one hour.
        start = datetime.datetime(2025, 12, 24, 0, 10, 0).timestamp()
        end = datetime.datetime(2025, 12, 24, 3, 10, 0).timestamp()
        parts = split_interval_by_local_hour(start, end)
        per_hour = {}
        total = 0.0
        for day, hour, seconds in parts:
            per_hour[(day, hour)] = per_hour.get((day, hour), 0.0) + seconds
            total += seconds
        self.assertAlmostEqual(total, end - start, places=6)
        self.assertTrue(all(s <= 3600.0 + 1e-6 for s in per_hour.values()))

    def test_tracker_flush_buckets_by_hour(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            tracker = ActivityTrack(path)
            start = datetime.datetime(2025, 12, 24, 0, 10, 0).timestamp()
            end = datetime.datetime(2025, 12, 24, 3, 10, 0).timestamp()

            with tracker.lock:
                tracker._add_foreground_duration("dummy.exe", start, end)

            tracker.flush_stats()

            # Verify DB hour totals are physically plausible (<= 3600)
            import sqlite3

            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute(
                "SELECT hour, SUM(duration_seconds) FROM app_foreground_time WHERE date=? GROUP BY hour ORDER BY hour",
                ("2025-12-24",),
            )
            rows = cur.fetchall()
            conn.close()

            self.assertGreaterEqual(len(rows), 1)
            self.assertTrue(all(total <= 3600 for _hour, total in rows))
            self.assertEqual(sum(total for _hour, total in rows), int(end - start))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()

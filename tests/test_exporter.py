"""
Tests for the DataExporter module.
"""

import os
import sys
import json
import csv
import tempfile
import datetime
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.exporter import DataExporter


def create_test_database():
    """Create a temporary file-based database for testing."""
    # Use a temp file instead of :memory: since SQLite in-memory databases
    # don't persist across different connections
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)
    return temp_path


class TestDataExporter(unittest.TestCase):
    """Test cases for DataExporter class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Create file-based database for testing (in-memory doesn't persist)
        cls.db_path = create_test_database()
        cls.db = Database(cls.db_path)
        cls.exporter = DataExporter(cls.db)
        
        # Populate with test data
        cls._populate_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        try:
            cls.db.close()
        except Exception:
            pass
        try:
            os.remove(cls.db_path)
        except Exception:
            pass
    
    @classmethod
    def _populate_test_data(cls):
        """Populate database with test data."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        # Add daily stats
        cls.db.update_stats(today, key_count=1000, click_count=200, distance=50.5, scroll=150.0)
        cls.db.update_stats(yesterday, key_count=800, click_count=180, distance=45.0, scroll=120.0)
        
        # Add app stats
        cls.db.update_app_stats(today, "notepad.exe", key_count=500, click_count=50, scroll_count=30, distance=10)
        cls.db.update_app_stats(today, "chrome.exe", key_count=400, click_count=120, scroll_count=80, distance=35)
        cls.db.update_app_stats(yesterday, "notepad.exe", key_count=300, click_count=40, scroll_count=25, distance=8)
        cls.db.update_app_stats(yesterday, "vscode.exe", key_count=500, click_count=140, scroll_count=95, distance=37)
        
        # Add heatmap data (scan codes for common keys)
        cls.db.update_heatmap(today, 30, 100)  # 'A' key
        cls.db.update_heatmap(today, 31, 80)   # 'S' key
        cls.db.update_heatmap(today, 32, 60)   # 'D' key
        cls.db.update_heatmap(yesterday, 30, 90)
        cls.db.update_heatmap(yesterday, 33, 70)  # 'F' key
        
        # Add screen time / foreground time data
        cls.db.update_foreground_time(today, 10, "notepad.exe", 1800)  # 30 min
        cls.db.update_foreground_time(today, 11, "chrome.exe", 3600)   # 1 hour
        cls.db.update_foreground_time(yesterday, 14, "vscode.exe", 7200)  # 2 hours
        
        # Add app metadata
        cls.db.update_app_metadata("notepad.exe", "Notepad", "C:\\Windows\\System32\\notepad.exe")
        cls.db.update_app_metadata("chrome.exe", "Google Chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        cls.db.update_app_metadata("vscode.exe", "Visual Studio Code", "C:\\Users\\user\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe")
    
    def setUp(self):
        """Set up for each test."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # ==================== CSV Export Tests ====================
    
    def test_export_daily_stats_csv(self):
        """Test daily stats CSV export."""
        filepath = os.path.join(self.temp_dir, "daily_stats.csv")
        
        result = self.exporter.export_daily_stats_csv(filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        # Verify content
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Header + 2 data rows
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ['Date', 'Keystrokes', 'Mouse Clicks', 'Mouse Distance (m)', 'Scroll Distance'])
        
        # Check data values
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        dates = [rows[1][0], rows[2][0]]
        self.assertIn(str(yesterday), dates)
        self.assertIn(str(today), dates)
        
        # Verify dates are in ISO format (YYYY-MM-DD)
        for date_str in dates:
            # Should match YYYY-MM-DD pattern
            self.assertRegex(date_str, r'^\d{4}-\d{2}-\d{2}$')
    
    def test_export_daily_stats_csv_with_date_range(self):
        """Test daily stats CSV export with date range."""
        filepath = os.path.join(self.temp_dir, "daily_stats_range.csv")
        today = datetime.date.today()
        
        result = self.exporter.export_daily_stats_csv(filepath, today, today)
        
        self.assertTrue(result)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Header + 1 data row (today only)
        self.assertEqual(len(rows), 2)
    
    def test_export_app_stats_csv(self):
        """Test app stats CSV export."""
        filepath = os.path.join(self.temp_dir, "app_stats.csv")
        
        result = self.exporter.export_app_stats_csv(filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Header + 3 apps
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], ['Application', 'Friendly Name', 'Keystrokes', 'Clicks', 'Scrolls', 'Distance (m)'])
        
        # Check that friendly names are included
        app_names = [row[0] for row in rows[1:]]
        friendly_names = [row[1] for row in rows[1:]]
        
        self.assertIn("notepad.exe", app_names)
        self.assertIn("chrome.exe", app_names)
        self.assertIn("Notepad", friendly_names)
    
    def test_export_heatmap_csv(self):
        """Test keyboard heatmap CSV export."""
        filepath = os.path.join(self.temp_dir, "heatmap.csv")
        
        result = self.exporter.export_heatmap_csv(filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Header + at least 4 key codes
        self.assertGreaterEqual(len(rows), 5)
        self.assertEqual(rows[0], ['Key Code (Scan Code)', 'Press Count'])
        
        # Check that scan code 30 (A key) has the highest count
        key_code_30_row = next((row for row in rows[1:] if row[0] == '30'), None)
        self.assertIsNotNone(key_code_30_row)
        self.assertEqual(int(key_code_30_row[1]), 190)  # 100 + 90 from today + yesterday
    
    def test_export_screen_time_csv(self):
        """Test screen time CSV export."""
        filepath = os.path.join(self.temp_dir, "screen_time.csv")
        
        result = self.exporter.export_screen_time_csv(filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Header + 3 apps
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], ['Application', 'Friendly Name', 'Total Seconds', 'Formatted Time'])
        
        # Check vscode has 2 hours = 7200 seconds
        vscode_row = next((row for row in rows[1:] if row[0] == 'vscode.exe'), None)
        self.assertIsNotNone(vscode_row)
        self.assertEqual(int(vscode_row[2]), 7200)
        self.assertEqual(vscode_row[3], '02:00:00')
    
    def test_export_all_csv(self):
        """Test exporting all data to CSV files."""
        results = self.exporter.export_all_csv(self.temp_dir)
        
        self.assertTrue(all(results.values()))
        
        # Check all files were created
        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 4)
        
        file_prefixes = [f.split('_')[0] for f in files if f.endswith('.csv')]
        self.assertIn('daily', file_prefixes)
        self.assertIn('app', file_prefixes)
        self.assertIn('heatmap', file_prefixes)
        self.assertIn('screen', file_prefixes)
    
    # ==================== JSON Export Tests ====================
    
    def test_export_json(self):
        """Test JSON export."""
        filepath = os.path.join(self.temp_dir, "export.json")
        
        result = self.exporter.export_json(filepath)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check structure
        self.assertIn('export_info', data)
        self.assertIn('daily_stats', data)
        self.assertIn('app_stats', data)
        self.assertIn('keyboard_heatmap', data)
        self.assertIn('screen_time', data)
        
        # Check export info
        self.assertEqual(data['export_info']['version'], '1.0')
        self.assertIn('exported_at', data['export_info'])
        
        # Check daily stats
        self.assertEqual(len(data['daily_stats']), 2)
        today_stat = next((s for s in data['daily_stats'] if s['date'] == str(datetime.date.today())), None)
        self.assertIsNotNone(today_stat)
        self.assertEqual(today_stat['keystrokes'], 1000)
        self.assertEqual(today_stat['mouse_clicks'], 200)
        
        # Check app stats
        self.assertEqual(len(data['app_stats']), 3)
        notepad_stat = next((s for s in data['app_stats'] if s['app_name'] == 'notepad.exe'), None)
        self.assertIsNotNone(notepad_stat)
        self.assertEqual(notepad_stat['friendly_name'], 'Notepad')
        self.assertEqual(notepad_stat['keystrokes'], 800)  # 500 + 300
        
        # Check heatmap
        self.assertGreaterEqual(len(data['keyboard_heatmap']), 4)
        
        # Check screen time
        self.assertEqual(len(data['screen_time']), 3)
    
    def test_export_json_with_date_range(self):
        """Test JSON export with date range."""
        filepath = os.path.join(self.temp_dir, "export_range.json")
        today = datetime.date.today()
        
        result = self.exporter.export_json(filepath, today, today)
        
        self.assertTrue(result)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check export info has date range
        self.assertEqual(data['export_info']['start_date'], str(today))
        self.assertEqual(data['export_info']['end_date'], str(today))
        
        # Should only have today's stats
        self.assertEqual(len(data['daily_stats']), 1)
        self.assertEqual(data['daily_stats'][0]['date'], str(today))
    
    # ==================== Error Handling Tests ====================
    
    def test_export_to_invalid_path(self):
        """Test export to invalid path returns False."""
        invalid_path = "/nonexistent/path/that/does/not/exist/file.csv"
        
        result = self.exporter.export_daily_stats_csv(invalid_path)
        
        self.assertFalse(result)
    
    def test_export_json_to_invalid_path(self):
        """Test JSON export to invalid path returns False."""
        invalid_path = "/nonexistent/path/that/does/not/exist/file.json"
        
        result = self.exporter.export_json(invalid_path)
        
        self.assertFalse(result)
    
    # ==================== Date Range Helper Tests ====================
    
    def test_get_date_range_today(self):
        """Test date range calculation for 'today'."""
        start, end = self.exporter._get_date_range('today')
        today = datetime.date.today()
        
        self.assertEqual(start, today)
        self.assertEqual(end, today)
    
    def test_get_date_range_week(self):
        """Test date range calculation for 'week'."""
        start, end = self.exporter._get_date_range('week')
        today = datetime.date.today()
        
        self.assertEqual(end, today)
        self.assertEqual((end - start).days, 6)
    
    def test_get_date_range_month(self):
        """Test date range calculation for 'month'."""
        start, end = self.exporter._get_date_range('month')
        today = datetime.date.today()
        
        self.assertEqual(end, today)
        self.assertEqual((end - start).days, 29)
    
    def test_get_date_range_year(self):
        """Test date range calculation for 'year'."""
        start, end = self.exporter._get_date_range('year')
        today = datetime.date.today()
        
        self.assertEqual(end, today)
        self.assertEqual((end - start).days, 364)
    
    def test_get_date_range_all(self):
        """Test date range calculation for 'all'."""
        start, end = self.exporter._get_date_range('all')
        
        self.assertIsNone(start)
        self.assertIsNone(end)
    
    # ==================== Empty Database Tests ====================
    
    def test_export_empty_database(self):
        """Test exporting from an empty database."""
        empty_db_path = create_test_database()
        try:
            empty_db = Database(empty_db_path)
            exporter = DataExporter(empty_db)
            
            filepath = os.path.join(self.temp_dir, "empty.csv")
            result = exporter.export_daily_stats_csv(filepath)
            
            self.assertTrue(result)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Should have header only
            self.assertEqual(len(rows), 1)
        finally:
            empty_db.close()
            os.remove(empty_db_path)
    
    def test_export_json_empty_database(self):
        """Test JSON export from an empty database."""
        empty_db_path = create_test_database()
        try:
            empty_db = Database(empty_db_path)
            exporter = DataExporter(empty_db)
            
            filepath = os.path.join(self.temp_dir, "empty.json")
            result = exporter.export_json(filepath)
            
            self.assertTrue(result)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # All arrays should be empty
            self.assertEqual(len(data['daily_stats']), 0)
            self.assertEqual(len(data['app_stats']), 0)
            self.assertEqual(len(data['keyboard_heatmap']), 0)
            self.assertEqual(len(data['screen_time']), 0)
        finally:
            empty_db.close()
            os.remove(empty_db_path)


class TestExporterIntegration(unittest.TestCase):
    """Integration tests for exporter with realistic data scenarios."""
    
    def test_large_dataset_export(self):
        """Test exporting a larger dataset."""
        db_path = create_test_database()
        try:
            db = Database(db_path)
            exporter = DataExporter(db)
            
            # Generate 30 days of data
            today = datetime.date.today()
            for i in range(30):
                date = today - datetime.timedelta(days=i)
                db.update_stats(date, key_count=1000+i*10, click_count=200+i*5, 
                              distance=50.0+i*0.5, scroll=100.0+i*2)
                
                # Add hourly data for each day
                for hour in range(24):
                    db.update_hourly_app_stats(date, hour, "app.exe", 
                                              key_count=50, clicks=10, scrolls=5, distance=2.0)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export all
                results = exporter.export_all_csv(temp_dir)
                self.assertTrue(all(results.values()))
                
                # Verify daily stats has 30 rows
                daily_file = [f for f in os.listdir(temp_dir) if 'daily_stats' in f][0]
                with open(os.path.join(temp_dir, daily_file), 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                self.assertEqual(len(rows), 31)  # 30 days + header
        finally:
            db.close()
            os.remove(db_path)
    
    def test_unicode_app_names(self):
        """Test exporting data with Unicode app names."""
        db_path = create_test_database()
        try:
            db = Database(db_path)
            exporter = DataExporter(db)
            
            today = datetime.date.today()
            # Add app with Unicode characters
            db.update_app_stats(today, "中文应用.exe", key_count=100)
            db.update_app_stats(today, "日本語アプリ.exe", key_count=200)
            db.update_app_metadata("中文应用.exe", "中文应用程序", "C:\\Apps\\中文应用.exe")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # CSV export
                csv_path = os.path.join(temp_dir, "unicode_apps.csv")
                result = exporter.export_app_stats_csv(csv_path)
                self.assertTrue(result)
                
                with open(csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.assertIn("中文应用.exe", content)
                self.assertIn("日本語アプリ.exe", content)
                
                # JSON export
                json_path = os.path.join(temp_dir, "unicode_apps.json")
                result = exporter.export_json(json_path)
                self.assertTrue(result)
                
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                app_names = [app['app_name'] for app in data['app_stats']]
                self.assertIn("中文应用.exe", app_names)
        finally:
            db.close()
            os.remove(db_path)


if __name__ == '__main__':
    unittest.main()

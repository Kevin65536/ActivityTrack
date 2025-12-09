import sqlite3
import datetime
import os

class Database:
    def __init__(self, db_path="tracker.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Daily stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    key_count INTEGER DEFAULT 0,
                    mouse_click_count INTEGER DEFAULT 0,
                    mouse_distance REAL DEFAULT 0.0,
                    scroll_distance REAL DEFAULT 0.0
                )
            ''')
            
            # App stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_stats (
                    date DATE,
                    app_name TEXT,
                    key_count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, app_name)
                )
            ''')
            
            # Heatmap data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS heatmap_data (
                    date DATE,
                    key_code INTEGER,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, key_code)
                )
            ''')
            
            # Mouse Heatmap data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mouse_heatmap_data (
                    date DATE,
                    x INTEGER,
                    y INTEGER,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, x, y)
                )
            ''')
            conn.commit()
            
            # Migration for new columns in app_stats
            self._migrate_app_stats_schema()

    def _migrate_app_stats_schema(self):
        """Add new columns to app_stats if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Check if columns exist
                cursor.execute("PRAGMA table_info(app_stats)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if 'clicks' not in columns:
                    cursor.execute("ALTER TABLE app_stats ADD COLUMN clicks INTEGER DEFAULT 0")
                if 'scrolls' not in columns:
                    cursor.execute("ALTER TABLE app_stats ADD COLUMN scrolls INTEGER DEFAULT 0")
                if 'distance' not in columns:
                    cursor.execute("ALTER TABLE app_stats ADD COLUMN distance INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.Error as e:
                print(f"Migration warning: {e}")

    def update_stats(self, date, key_count=0, click_count=0, distance=0.0, scroll=0.0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO daily_stats (date, key_count, mouse_click_count, mouse_distance, scroll_distance)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    key_count = key_count + excluded.key_count,
                    mouse_click_count = mouse_click_count + excluded.mouse_click_count,
                    mouse_distance = mouse_distance + excluded.mouse_distance,
                    scroll_distance = scroll_distance + excluded.scroll_distance
            ''', (date, key_count, click_count, distance, scroll))
            conn.commit()

    def update_app_stats(self, date, app_name, key_count=0, click_count=0, scroll_count=0, distance=0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_stats (date, app_name, key_count, clicks, scrolls, distance)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, app_name) DO UPDATE SET
                    key_count = key_count + excluded.key_count,
                    clicks = clicks + excluded.clicks,
                    scrolls = scrolls + excluded.scrolls,
                    distance = distance + excluded.distance
            ''', (date, app_name, key_count, click_count, scroll_count, distance))
            conn.commit()

    def update_heatmap(self, date, key_code, count):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO heatmap_data (date, key_code, count)
                VALUES (?, ?, ?)
                ON CONFLICT(date, key_code) DO UPDATE SET
                    count = count + excluded.count
            ''', (date, key_code, count))

            conn.commit()

    def update_mouse_heatmap(self, date, x, y, count):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mouse_heatmap_data (date, x, y, count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, x, y) DO UPDATE SET
                    count = count + excluded.count
            ''', (date, x, y, count))
            conn.commit()

    def get_today_stats(self):
        today = datetime.date.today()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
            return cursor.fetchone()

    def get_weekly_stats(self):
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=6)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT date, key_count FROM daily_stats WHERE date BETWEEN ? AND ? ORDER BY date', (start_date, today))
            return cursor.fetchall()

    def get_today_heatmap(self):
        """Get today's keyboard heatmap data from database."""
        today = datetime.date.today()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key_code, count FROM heatmap_data WHERE date = ?', (today,))
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    def get_heatmap_range(self, start_date, end_date):
        """Get aggregated heatmap data for a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT key_code, SUM(count) as total_count 
                FROM heatmap_data 
                WHERE date BETWEEN ? AND ? 
                GROUP BY key_code
            ''', (start_date, end_date))
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    def get_today_mouse_heatmap(self):
        """Get today's mouse heatmap data from database."""
        today = datetime.date.today()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT x, y, count FROM mouse_heatmap_data WHERE date = ?', (today,))
            return cursor.fetchall()

    def get_mouse_heatmap_range(self, start_date, end_date):
        """Get aggregated mouse heatmap data for a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT x, y, SUM(count) as total_count 
                FROM mouse_heatmap_data 
                WHERE date BETWEEN ? AND ? 
                GROUP BY x, y
            ''', (start_date, end_date))
            return cursor.fetchall()

    def get_stats_range(self, start_date, end_date):
        """Get aggregated stats for a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    SUM(key_count) as total_keys,
                    SUM(mouse_click_count) as total_clicks,
                    SUM(mouse_distance) as total_distance,
                    SUM(scroll_distance) as total_scroll
                FROM daily_stats 
                WHERE date BETWEEN ? AND ?
            ''', (start_date, end_date))
            return cursor.fetchone()

    def get_weekly_summary(self):
        """Get this week's aggregated statistics (last 7 days)."""
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=6)
        return self.get_stats_range(start_date, today)

    def get_monthly_summary(self):
        """Get this month's aggregated statistics (last 30 days)."""
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=29)
        return self.get_stats_range(start_date, today)

    def get_all_time_stats(self):
        """Get all-time aggregated statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    SUM(key_count) as total_keys,
                    SUM(mouse_click_count) as total_clicks,
                    SUM(mouse_distance) as total_distance,
                    SUM(scroll_distance) as total_scroll,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(DISTINCT date) as days_tracked
                FROM daily_stats
            ''')
            return cursor.fetchone()

    def get_top_apps(self, limit=10, start_date=None, end_date=None):
        """Get top applications by keystroke count within a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if start_date and end_date:
                cursor.execute('''
                    SELECT app_name, SUM(key_count) as total_keys
                    FROM app_stats 
                    WHERE date BETWEEN ? AND ?
                    GROUP BY app_name
                    ORDER BY total_keys DESC
                    LIMIT ?
                ''', (start_date, end_date, limit))
            else:
                cursor.execute('''
                    SELECT app_name, SUM(key_count) as total_keys
                    FROM app_stats 
                    GROUP BY app_name
                    ORDER BY total_keys DESC
                    LIMIT ?
                ''', (limit,))
            return cursor.fetchall()

    def get_app_stats_summary(self, limit=50, start_date=None, end_date=None):
        """Get detailed app stats within a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if start_date and end_date:
                cursor.execute('''
                    SELECT 
                        app_name, 
                        SUM(key_count) as keys,
                        SUM(clicks) as clicks,
                        SUM(scrolls) as scrolls,
                        SUM(distance) as distance
                    FROM app_stats 
                    WHERE date BETWEEN ? AND ?
                    GROUP BY app_name
                    ORDER BY keys DESC
                    LIMIT ?
                ''', (start_date, end_date, limit))
            else:
                # All time (or default view logic if needed, but currently unused without range)
                cursor.execute('''
                    SELECT 
                        app_name, 
                        SUM(key_count) as keys,
                        SUM(clicks) as clicks,
                        SUM(scrolls) as scrolls,
                        SUM(distance) as distance
                    FROM app_stats 
                    GROUP BY app_name
                    ORDER BY keys DESC
                    LIMIT ?
                ''', (limit,))
            return cursor.fetchall()

    def get_daily_history(self, start_date=None, end_date=None):
        """Get daily statistics for trend charts. Returns list of (date, keys, clicks, distance, scroll)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if start_date and end_date:
                cursor.execute('''
                    SELECT date, key_count, mouse_click_count, mouse_distance, scroll_distance
                    FROM daily_stats 
                    WHERE date BETWEEN ? AND ?
                    ORDER BY date ASC
                ''', (start_date, end_date))
            else:
                cursor.execute('''
                    SELECT date, key_count, mouse_click_count, mouse_distance, scroll_distance
                    FROM daily_stats 
                    ORDER BY date ASC
                ''')
            return cursor.fetchall()

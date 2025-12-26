import sqlite3
import datetime
import os
import sys

class Database:
    def __init__(self, db_path="tracker.db"):
        self.db_path = self._resolve_db_path(db_path)
        self.init_db()

    def _resolve_db_path(self, db_path):
        """Ensure DB path is anchored to the install directory."""
        if db_path == ":memory:":
            return db_path
        if os.path.isabs(db_path):
            return db_path

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        return os.path.join(base_dir, db_path)

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
            
            # App-specific keyboard heatmap data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_heatmap_data (
                    date DATE,
                    app_name TEXT,
                    key_code INTEGER,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, app_name, key_code)
                )
            ''')
            
            # App-specific mouse heatmap data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_mouse_heatmap_data (
                    date DATE,
                    app_name TEXT,
                    x INTEGER,
                    y INTEGER,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, app_name, x, y)
                )
            ''')
            conn.commit()
            
            # Migration for new columns in app_stats
            self._migrate_app_stats_schema()
            
            # Hourly App Stats table for granular tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_app_stats (
                    date DATE,
                    hour INTEGER,
                    app_name TEXT,
                    key_count INTEGER DEFAULT 0,
                    clicks INTEGER DEFAULT 0,
                    scrolls INTEGER DEFAULT 0,
                    distance REAL DEFAULT 0.0,
                    PRIMARY KEY (date, hour, app_name)
                )
            ''')
            
            # Ensure app_metadata table exists
            self._migrate_app_metadata_schema()
            
            # App foreground time table for screen time tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_foreground_time (
                    date DATE,
                    hour INTEGER,
                    app_name TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    PRIMARY KEY (date, hour, app_name)
                )
            ''')
            
            conn.commit()

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

    def update_hourly_app_stats(self, date, hour, app_name, key_count=0, clicks=0, scrolls=0, distance=0.0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO hourly_app_stats (date, hour, app_name, key_count, clicks, scrolls, distance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, hour, app_name) DO UPDATE SET
                    key_count = key_count + excluded.key_count,
                    clicks = clicks + excluded.clicks,
                    scrolls = scrolls + excluded.scrolls,
                    distance = distance + excluded.distance
            ''', (date, hour, app_name, key_count, clicks, scrolls, distance))
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

    def update_app_heatmap(self, date, app_name, key_code, count):
        """Update app-specific keyboard heatmap data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_heatmap_data (date, app_name, key_code, count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, app_name, key_code) DO UPDATE SET
                    count = count + excluded.count
            ''', (date, app_name, key_code, count))
            conn.commit()

    def update_app_mouse_heatmap(self, date, app_name, x, y, count):
        """Update app-specific mouse heatmap data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_mouse_heatmap_data (date, app_name, x, y, count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, app_name, x, y) DO UPDATE SET
                    count = count + excluded.count
            ''', (date, app_name, x, y, count))
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

    def get_heatmap_range(self, start_date, end_date, app_filter=None):
        """Get aggregated heatmap data for a date range, optionally filtered by app."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT key_code, SUM(count) as total_count 
                    FROM app_heatmap_data 
                    WHERE date BETWEEN ? AND ? AND app_name = ?
                    GROUP BY key_code
                ''', (start_date, end_date, app_filter))
            else:
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

    def get_mouse_heatmap_range(self, start_date, end_date, app_filter=None):
        """Get aggregated mouse heatmap data for a date range, optionally filtered by app."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT x, y, SUM(count) as total_count 
                    FROM app_mouse_heatmap_data 
                    WHERE date BETWEEN ? AND ? AND app_name = ?
                    GROUP BY x, y
                ''', (start_date, end_date, app_filter))
            else:
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

    def get_daily_history(self, start_date=None, end_date=None, app_filter=None):
        """Get daily statistics for trend charts. Returns list of (date, keys, clicks, distance, scroll)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if app_filter and app_filter != "All Applications":
                if start_date and end_date:
                    cursor.execute('''
                        SELECT date, SUM(key_count), SUM(clicks), SUM(distance), SUM(scrolls)
                        FROM app_stats 
                        WHERE app_name = ? AND date BETWEEN ? AND ?
                        GROUP BY date
                        ORDER BY date ASC
                    ''', (app_filter, start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT date, SUM(key_count), SUM(clicks), SUM(distance), SUM(scrolls)
                        FROM app_stats 
                        WHERE app_name = ?
                        GROUP BY date
                        ORDER BY date ASC
                    ''', (app_filter,))
            else:
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

    def get_today_hourly_stats(self, app_filter=None):
        """Get today's hourly stats: [(hour, keys, clicks), ...]"""
        today = datetime.date.today()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT hour, SUM(key_count), SUM(clicks)
                    FROM hourly_app_stats
                    WHERE date = ? AND app_name = ?
                    GROUP BY hour
                    ORDER BY hour ASC
                ''', (today, app_filter))
            else:
                cursor.execute('''
                    SELECT hour, SUM(key_count), SUM(clicks)
                    FROM hourly_app_stats
                    WHERE date = ?
                    GROUP BY hour
                    ORDER BY hour ASC
                ''', (today,))
            return cursor.fetchall()

    def get_day_of_week_averages(self, app_filter=None):
        """Get average stats per day of week (0=Sunday, 6=Saturday in SQLite strftime %w)."""
        # Note: SQLite %w returns 0-6 where 0 is Sunday.
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                # Average per day for specific app involves summing for each date then averaging by DOW
                # But querying raw app_stats is easier:
                cursor.execute('''
                    SELECT 
                        strftime('%w', date) as dow,
                        AVG(key_count),
                        AVG(clicks)
                    FROM app_stats
                    WHERE app_name = ?
                    GROUP BY dow
                    ORDER BY dow
                ''', (app_filter,))
            else:
                cursor.execute('''
                    SELECT 
                        strftime('%w', date) as dow,
                        AVG(key_count),
                        AVG(mouse_click_count)
                    FROM daily_stats
                    GROUP BY dow
                    ORDER BY dow
                ''')
            return cursor.fetchall()

    def get_hour_of_day_averages(self, app_filter=None):
        """Get average stats per hour of day over history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT hour, AVG(key_count), AVG(clicks)
                    FROM hourly_app_stats
                    WHERE app_name = ?
                    GROUP BY hour
                    ORDER BY hour
                ''', (app_filter,))
            else:
                # Sum all apps for each (date, hour) first, then average?
                # Or just average over all (date, hour) records? 
                # Be careful: hourly_app_stats has one row per app per hour.
                # To get global hourly average, we first need to sum across apps for each (date, hour), then average those sums.
                cursor.execute('''
                    WITH hourly_sums AS (
                        SELECT date, hour, SUM(key_count) as total_keys, SUM(clicks) as total_clicks
                        FROM hourly_app_stats
                        GROUP BY date, hour
                    )
                    SELECT hour, AVG(total_keys), AVG(total_clicks)
                    FROM hourly_sums
                    GROUP BY hour
                    ORDER BY hour
                ''')
            return cursor.fetchall()

    def get_all_apps(self):
        """Get list of all unique app names for dropdown."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Try to return friendly names if available, else app_name
            # But grouping is by app_name. UI can look up friendly name.
            # Let's just return app_name sorted.
            cursor.execute('SELECT DISTINCT app_name FROM app_stats ORDER BY app_name')
            return [row[0] for row in cursor.fetchall()]

    def get_apps_by_date_range(self, start_date=None, end_date=None):
        """Get list of unique app names that have activity within the date range."""
        if start_date is None or end_date is None:
            return self.get_all_apps()
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT app_name 
                FROM app_stats 
                WHERE date BETWEEN ? AND ? 
                ORDER BY app_name
            ''', (start_date, end_date))
            return [row[0] for row in cursor.fetchall()]

    def _migrate_app_metadata_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_metadata (
                    app_name TEXT PRIMARY KEY,
                    friendly_name TEXT,
                    exe_path TEXT
                )
            ''')
            conn.commit()

    def update_app_metadata(self, app_name, friendly_name, exe_path):
        """Update or insert app metadata."""
        # Ensure schema exists (lazy init or call in init_db)
        # Calling here is safe but a bit redundant, usually call in init_db.
        # But since we are patching, let's call it once in init_db or here.
        # Let's add it to init_db actually, but since I am editing here...
        # I'll rely on init_db calling it if I add it there, or just call it.
        # Let's just execute the create if not exists here to be safe for this patch.
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_metadata (
                    app_name TEXT PRIMARY KEY,
                    friendly_name TEXT,
                    exe_path TEXT
                )
            ''')
            cursor.execute('''
                INSERT INTO app_metadata (app_name, friendly_name, exe_path)
                VALUES (?, ?, ?)
                ON CONFLICT(app_name) DO UPDATE SET
                    friendly_name = excluded.friendly_name,
                    exe_path = excluded.exe_path
            ''', (app_name, friendly_name, exe_path))
            conn.commit()

    def get_app_metadata_dict(self):
        """Return dict {app_name: {'friendly_name': ..., 'exe_path': ...}}."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check table exists first
            try:
                cursor.execute("SELECT app_name, friendly_name, exe_path FROM app_metadata")
                rows = cursor.fetchall()
                return {row[0]: {'friendly_name': row[1], 'exe_path': row[2]} for row in rows}
            except sqlite3.OperationalError:
                return {}

    # ==================== Screen Time / Foreground Time Methods ====================
    
    def update_foreground_time(self, date, hour, app_name, duration_seconds):
        """Update app foreground time for a specific date and hour."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_foreground_time (date, hour, app_name, duration_seconds)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, hour, app_name) DO UPDATE SET
                    duration_seconds = duration_seconds + excluded.duration_seconds
            ''', (date, hour, app_name, duration_seconds))
            conn.commit()

    def get_foreground_time_by_app(self, start_date, end_date):
        """Get total foreground time per app within date range. Returns list of (app_name, total_seconds)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT app_name, SUM(duration_seconds) as total_seconds
                FROM app_foreground_time
                WHERE date BETWEEN ? AND ?
                GROUP BY app_name
                ORDER BY total_seconds DESC
            ''', (start_date, end_date))
            return cursor.fetchall()

    def get_foreground_time_hourly(self, date, app_filter=None):
        """Get hourly foreground time for a specific date. Returns list of (hour, total_seconds)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT hour, SUM(duration_seconds) as total_seconds
                    FROM app_foreground_time
                    WHERE date = ? AND app_name = ?
                    GROUP BY hour
                    ORDER BY hour ASC
                ''', (date, app_filter))
            else:
                cursor.execute('''
                    SELECT hour, SUM(duration_seconds) as total_seconds
                    FROM app_foreground_time
                    WHERE date = ?
                    GROUP BY hour
                    ORDER BY hour ASC
                ''', (date,))
            return cursor.fetchall()

    def get_foreground_time_daily(self, start_date, end_date, app_filter=None):
        """Get daily foreground time for date range. Returns list of (date, total_seconds)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT date, SUM(duration_seconds) as total_seconds
                    FROM app_foreground_time
                    WHERE date BETWEEN ? AND ? AND app_name = ?
                    GROUP BY date
                    ORDER BY date ASC
                ''', (start_date, end_date, app_filter))
            else:
                cursor.execute('''
                    SELECT date, SUM(duration_seconds) as total_seconds
                    FROM app_foreground_time
                    WHERE date BETWEEN ? AND ?
                    GROUP BY date
                    ORDER BY date ASC
                ''', (start_date, end_date))
            return cursor.fetchall()

    def get_total_foreground_time(self, start_date, end_date, app_filter=None):
        """Get total foreground time for date range in seconds."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if app_filter and app_filter != "All Applications":
                cursor.execute('''
                    SELECT SUM(duration_seconds)
                    FROM app_foreground_time
                    WHERE date BETWEEN ? AND ? AND app_name = ?
                ''', (start_date, end_date, app_filter))
            else:
                cursor.execute('''
                    SELECT SUM(duration_seconds)
                    FROM app_foreground_time
                    WHERE date BETWEEN ? AND ?
                ''', (start_date, end_date))
            result = cursor.fetchone()
            return result[0] or 0

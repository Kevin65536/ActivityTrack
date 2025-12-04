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
            conn.commit()

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

    def update_app_stats(self, date, app_name, key_count):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_stats (date, app_name, key_count)
                VALUES (?, ?, ?)
                ON CONFLICT(date, app_name) DO UPDATE SET
                    key_count = key_count + excluded.key_count
            ''', (date, app_name, key_count))
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

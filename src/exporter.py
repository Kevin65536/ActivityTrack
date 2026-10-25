"""
Data export module for ActivityTrack.
Provides CSV, JSON, and image export functionality.
"""

import csv
import json
import os
import datetime
from typing import Optional, Dict, List, Any, Tuple


class DataExporter:
    """Handles data export operations for ActivityTrack."""
    
    def __init__(self, database):
        """Initialize exporter with database reference.
        
        Args:
            database: Database instance to export data from
        """
        self.db = database
    
    def _get_date_range(self, range_type: str) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
        """Convert range type string to date range.
        
        Args:
            range_type: One of 'today', 'week', 'month', 'year', 'all'
            
        Returns:
            Tuple of (start_date, end_date), both may be None for 'all'
        """
        today = datetime.date.today()
        if range_type == 'today':
            return today, today
        elif range_type == 'week':
            return today - datetime.timedelta(days=6), today
        elif range_type == 'month':
            return today - datetime.timedelta(days=29), today
        elif range_type == 'year':
            return today - datetime.timedelta(days=364), today
        else:  # 'all'
            return None, None
    
    def export_daily_stats_csv(self, filepath: str, start_date: Optional[datetime.date] = None, 
                                end_date: Optional[datetime.date] = None) -> bool:
        """Export daily statistics to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.read_connection() as conn:
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
                
                rows = cursor.fetchall()
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Date', 'Keystrokes', 'Mouse Clicks', 'Mouse Distance (m)', 'Scroll Distance'])
                    for row in rows:
                        # Ensure date is formatted as ISO string (YYYY-MM-DD)
                        date_val = row[0]
                        if hasattr(date_val, 'isoformat'):
                            date_str = date_val.isoformat()
                        else:
                            date_str = str(date_val)
                        writer.writerow([date_str, row[1], row[2], row[3], row[4]])
                
                return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def export_app_stats_csv(self, filepath: str, start_date: Optional[datetime.date] = None,
                              end_date: Optional[datetime.date] = None) -> bool:
        """Export application statistics to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.read_connection() as conn:
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
                    ''', (start_date, end_date))
                else:
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
                    ''')
                
                rows = cursor.fetchall()
                
                # Get metadata for friendly names
                metadata = self.db.get_app_metadata_dict(connection=conn)
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Application', 'Friendly Name', 'Keystrokes', 'Clicks', 'Scrolls', 'Distance (m)'])
                    for row in rows:
                        app_name = row[0]
                        friendly_name = metadata.get(app_name, {}).get('friendly_name', '')
                        writer.writerow([app_name, friendly_name, row[1] or 0, row[2] or 0, row[3] or 0, row[4] or 0])
                
                return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def export_heatmap_csv(self, filepath: str, start_date: Optional[datetime.date] = None,
                            end_date: Optional[datetime.date] = None) -> bool:
        """Export keyboard heatmap data to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.read_connection() as conn:
                cursor = conn.cursor()
                
                if start_date and end_date:
                    cursor.execute('''
                        SELECT key_code, SUM(count) as total_count
                        FROM heatmap_data
                        WHERE date BETWEEN ? AND ?
                        GROUP BY key_code
                        ORDER BY total_count DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT key_code, SUM(count) as total_count
                        FROM heatmap_data
                        GROUP BY key_code
                        ORDER BY total_count DESC
                    ''')
                
                rows = cursor.fetchall()
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Key Code (Scan Code)', 'Press Count'])
                    for row in rows:
                        writer.writerow(row)
                
                return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def export_screen_time_csv(self, filepath: str, start_date: Optional[datetime.date] = None,
                                end_date: Optional[datetime.date] = None) -> bool:
        """Export screen time / foreground time data to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.read_connection() as conn:
                cursor = conn.cursor()
                
                if start_date and end_date:
                    cursor.execute('''
                        SELECT app_name, SUM(duration_seconds) as total_seconds
                        FROM app_foreground_time
                        WHERE date BETWEEN ? AND ?
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT app_name, SUM(duration_seconds) as total_seconds
                        FROM app_foreground_time
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                    ''')
                
                rows = cursor.fetchall()
                
                # Get metadata for friendly names
                metadata = self.db.get_app_metadata_dict(connection=conn)
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Application', 'Friendly Name', 'Total Seconds', 'Formatted Time'])
                    for row in rows:
                        app_name = row[0]
                        total_seconds = row[1] or 0
                        if float(total_seconds).is_integer():
                            total_seconds = int(total_seconds)
                        friendly_name = metadata.get(app_name, {}).get('friendly_name', '')
                        
                        # Format time as HH:MM:SS
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        seconds = int(total_seconds % 60)
                        formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        writer.writerow([app_name, friendly_name, total_seconds, formatted])
                
                return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def export_all_csv(self, directory: str, start_date: Optional[datetime.date] = None,
                        end_date: Optional[datetime.date] = None) -> Dict[str, bool]:
        """Export all data types to CSV files in the given directory.
        
        Args:
            directory: Directory to save CSV files
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            Dict mapping filename to success status
        """
        os.makedirs(directory, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results = {}
        
        # Export daily stats
        filepath = os.path.join(directory, f"daily_stats_{timestamp}.csv")
        results['daily_stats'] = self.export_daily_stats_csv(filepath, start_date, end_date)
        
        # Export app stats
        filepath = os.path.join(directory, f"app_stats_{timestamp}.csv")
        results['app_stats'] = self.export_app_stats_csv(filepath, start_date, end_date)
        
        # Export heatmap
        filepath = os.path.join(directory, f"heatmap_{timestamp}.csv")
        results['heatmap'] = self.export_heatmap_csv(filepath, start_date, end_date)
        
        # Export screen time
        filepath = os.path.join(directory, f"screen_time_{timestamp}.csv")
        results['screen_time'] = self.export_screen_time_csv(filepath, start_date, end_date)
        
        return results
    
    def export_json(self, filepath: str, start_date: Optional[datetime.date] = None,
                     end_date: Optional[datetime.date] = None) -> bool:
        """Export all data to a single JSON file.
        
        Args:
            filepath: Path to save the JSON file
            start_date: Start date for export (None for all time)
            end_date: End date for export (None for all time)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'export_info': {
                    'exported_at': datetime.datetime.now().isoformat(),
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None,
                    'version': '1.0'
                },
                'daily_stats': [],
                'app_stats': [],
                'keyboard_heatmap': [],
                'screen_time': []
            }
            
            with self.db.read_connection() as conn:
                cursor = conn.cursor()
                
                # Daily stats
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
                
                for row in cursor.fetchall():
                    data['daily_stats'].append({
                        'date': str(row[0]),
                        'keystrokes': row[1] or 0,
                        'mouse_clicks': row[2] or 0,
                        'mouse_distance': row[3] or 0,
                        'scroll_distance': row[4] or 0
                    })
                
                # App stats
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
                    ''', (start_date, end_date))
                else:
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
                    ''')
                
                metadata = self.db.get_app_metadata_dict(connection=conn)
                
                for row in cursor.fetchall():
                    app_name = row[0]
                    meta = metadata.get(app_name, {})
                    data['app_stats'].append({
                        'app_name': app_name,
                        'friendly_name': meta.get('friendly_name', ''),
                        'exe_path': meta.get('exe_path', ''),
                        'keystrokes': row[1] or 0,
                        'clicks': row[2] or 0,
                        'scrolls': row[3] or 0,
                        'distance': row[4] or 0
                    })
                
                # Keyboard heatmap
                if start_date and end_date:
                    cursor.execute('''
                        SELECT key_code, SUM(count) as total_count
                        FROM heatmap_data
                        WHERE date BETWEEN ? AND ?
                        GROUP BY key_code
                        ORDER BY total_count DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT key_code, SUM(count) as total_count
                        FROM heatmap_data
                        GROUP BY key_code
                        ORDER BY total_count DESC
                    ''')
                
                for row in cursor.fetchall():
                    data['keyboard_heatmap'].append({
                        'key_code': row[0],
                        'count': row[1] or 0
                    })
                
                # Screen time
                if start_date and end_date:
                    cursor.execute('''
                        SELECT app_name, SUM(duration_seconds) as total_seconds
                        FROM app_foreground_time
                        WHERE date BETWEEN ? AND ?
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT app_name, SUM(duration_seconds) as total_seconds
                        FROM app_foreground_time
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                    ''')
                
                for row in cursor.fetchall():
                    app_name = row[0]
                    total_seconds = row[1] or 0
                    meta = metadata.get(app_name, {})
                    data['screen_time'].append({
                        'app_name': app_name,
                        'friendly_name': meta.get('friendly_name', ''),
                        'total_seconds': total_seconds
                    })
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    

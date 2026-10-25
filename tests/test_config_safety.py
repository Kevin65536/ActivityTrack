import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.config import Config, DEFAULT_CONFIG
from src.exporter import DataExporter, csv_text
from src.database import Database


class ConfigSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = Config(self.directory.name)

    def test_nested_defaults_are_not_shared(self):
        groups = self.config.app_groups
        groups['productivity'].append('private.exe')
        self.assertEqual(self.config.app_groups['productivity'], [])
        self.config.app_groups = groups
        self.assertEqual(DEFAULT_CONFIG['app_groups']['productivity'], [])

    def test_invalid_loaded_values_use_defaults(self):
        Path(self.config.config_path).write_text(json.dumps({
            'idle_timeout_seconds': 'oops', 'minimize_to_tray': 'false',
            'app_groups': [], 'language': 'zh', 'data_retention_days': 0}), encoding='utf-8')
        with self.assertLogs('src.config', level='WARNING'):
            self.config.load()
        self.assertEqual(self.config.idle_timeout_seconds, 300)
        self.assertTrue(self.config.minimize_to_tray)
        self.assertEqual(self.config.language, 'zh')
        self.assertEqual(self.config.data_retention_days, -1)

    def test_atomic_save_failure_preserves_file_and_memory(self):
        self.config.save()
        before = Path(self.config.config_path).read_bytes()
        with patch('src.fileio.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.config.language = 'zh'
        self.assertEqual(Path(self.config.config_path).read_bytes(), before)
        self.assertEqual(self.config.language, 'en')
        self.assertEqual(list(Path(self.directory.name).glob('*.tmp')), [])

    def test_autostart_path_is_quoted(self):
        with patch.object(self.config, 'is_frozen', return_value=True), \
             patch.object(self.config, '_get_executable_path', return_value=r'C:\Program Files\ActivityTrack\ActivityTrack.exe'), \
             patch('src.config.winreg.OpenKey'), patch('src.config.winreg.CloseKey'), \
             patch('src.config.winreg.SetValueEx') as setter:
            self.assertTrue(self.config._update_autostart_registry(True)[0])
            self.assertEqual(setter.call_args.args[-1], '"C:\\Program Files\\ActivityTrack\\ActivityTrack.exe"')

    def test_csv_formula_escapes_and_json_is_lossless(self):
        for text in ('=1+1', '+cmd', '-1', '@SUM(A1)', ' \t=1', '\rdata', '＝1+1'):
            self.assertEqual(csv_text(text), "'" + text)
        self.assertEqual(csv_text('Example.exe'), 'Example.exe')
        self.assertEqual(csv_text(-3), -3)
        db = Database(str(Path(self.directory.name) / 'test.db'))
        self.addCleanup(db.close)
        db.update_app_stats('2026-10-25', '=1+1', key_count=1)
        exporter = DataExporter(db)
        output = Path(self.directory.name) / 'out.json'
        self.assertTrue(exporter.export_json(str(output)))
        self.assertIn('=1+1', output.read_text(encoding='utf-8'))

    def test_export_failure_preserves_existing_file(self):
        db = Database(str(Path(self.directory.name) / 'test.db'))
        self.addCleanup(db.close)
        output = Path(self.directory.name) / 'out.csv'
        output.write_text('original', encoding='utf-8')
        exporter = DataExporter(db)
        with patch('src.fileio.os.replace', side_effect=OSError('disk error')), \
             self.assertLogs('src.exporter', level='ERROR'):
            self.assertFalse(exporter.export_daily_stats_csv(str(output)))
        self.assertEqual(output.read_text(encoding='utf-8'), 'original')
        self.assertEqual(exporter.last_error, 'disk error')

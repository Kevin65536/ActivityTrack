from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from build import build_environment, validate_package


class PackagingSafetyTests(unittest.TestCase):
    def test_build_and_smoke_environments_exclude_unrelated_dll_paths(self):
        with patch.dict(os.environ, {'PATH': 'C:\\unrelated-tool', 'PYTHONPATH': 'C:\\other-python'}):
            environment = build_environment(include_python=False)
            self.assertNotIn('unrelated-tool', environment['PATH'])
            self.assertNotIn('PYTHONPATH', environment)
            self.assertEqual(os.environ['PATH'], 'C:\\unrelated-tool')

    def test_user_data_is_rejected_even_inside_internal_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ActivityTrack.exe').write_bytes(b'test')
            internal = root / '_internal'
            internal.mkdir()
            for name in ('tracker.db', 'tracker.db-wal', 'config.json', 'app_trace.txt', 'activitytrack.log'):
                with self.subTest(name=name):
                    sensitive = internal / name
                    sensitive.write_text('private', encoding='utf-8')
                    with self.assertRaises(ValueError):
                        validate_package(root)
                    sensitive.unlink()
            self.assertEqual(len(validate_package(root)), 1)

    def test_unexpected_root_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ActivityTrack.exe').write_bytes(b'test')
            (root / 'personal-export.csv').write_text('private', encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_package(root)

"""Tests for DependencyScanner."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_env.scanner import DependencyScanner
from .conftest import create_test_python_project, remove_test_dir


class TestDependencyScanner(unittest.TestCase):
    """Test cases for DependencyScanner."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = DependencyScanner()
        self.scanner.USER_OVERRIDE_FILE_PATH = Path(self.temp_dir) / 'user_override.local.json'
        self.scanner.packaged_mapping_file_path = Path(self.temp_dir) / 'package_name_mapping.json'
        self.scanner.packaged_mapping_file_path.write_text(
            json.dumps({'sklearn': 'scikit-learn', 'cv2': 'opencv-python', 'yaml': 'pyyaml'}),
            encoding='utf-8'
        )

    def tearDown(self):
        remove_test_dir(self.temp_dir)

    def test_scan_simple_imports_metadata_primary(self):
        files = {'main.py': 'import numpy\nimport pandas\nfrom sklearn import datasets'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(
            self.scanner,
            '_get_packages_distributions',
            return_value={'numpy': ['NumPy'], 'pandas': ['pandas'], 'sklearn': ['scikit_learn']}
        ):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertEqual(result['numpy'], 'numpy')
        self.assertEqual(result['pandas'], 'pandas')
        self.assertEqual(result['sklearn'], 'scikit-learn')

    def test_packaged_fallback_mapping_used_when_metadata_miss(self):
        files = {'code.py': 'import cv2\nimport yaml'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(self.scanner, '_get_packages_distributions', return_value={}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertEqual(result['cv2'], 'opencv-python')
        self.assertEqual(result['yaml'], 'pyyaml')

    def test_local_override_precedence_over_packaged_fallback(self):
        files = {'main.py': 'import demo'}
        create_test_python_project(self.temp_dir, files)

        override_file = Path(self.temp_dir) / '.create_env_mapping.local.json'
        override_file.write_text(json.dumps({'demo': 'demo-override'}), encoding='utf-8')

        with patch.object(self.scanner, '_get_packages_distributions', return_value={}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertEqual(result['demo'], 'demo-override')

    def test_ambiguous_metadata_mapping_warns_and_skips(self):
        files = {'main.py': 'import requests'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(
            self.scanner,
            '_get_packages_distributions',
            return_value={'requests': ['requests', 'requests-fork']}
        ):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertNotIn('requests', result)
        self.assertTrue(any('Ambiguous distribution mapping' in warning for warning in self.scanner.warnings))

    def test_unresolved_import_is_persisted_to_local_override(self):
        files = {'main.py': 'import unresolvedpkg'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(self.scanner, '_get_packages_distributions', return_value={}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertEqual(result, {})
        self.assertIn('unresolvedpkg', self.scanner.pending_mapping_updates)

        updated = self.scanner.persist_pending_mapping_updates()
        self.assertTrue(updated)

        override_file = Path(self.temp_dir) / '.create_env_mapping.local.json'
        saved_mapping = json.loads(override_file.read_text(encoding='utf-8'))
        self.assertIn('unresolvedpkg', saved_mapping)
        self.assertIsNone(saved_mapping['unresolvedpkg'])

    def test_invalid_mapping_entries_are_ignored_with_warning(self):
        files = {'main.py': 'import good\nimport bad'}
        create_test_python_project(self.temp_dir, files)

        override_file = Path(self.temp_dir) / '.create_env_mapping.local.json'
        override_file.write_text(
            json.dumps({
                'good': 'good-dist',
                'bad key': 'bad-dist',
                'bad': '',
            }),
            encoding='utf-8'
        )

        with patch.object(self.scanner, '_get_packages_distributions', return_value={}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertEqual(result['good'], 'good-dist')
        self.assertNotIn('bad', result)
        self.assertTrue(any('Ignored malformed mapping key' in warning for warning in self.scanner.warnings))
        self.assertTrue(any('Ignored malformed mapping value' in warning for warning in self.scanner.warnings))

    def test_ignore_stdlib_imports(self):
        files = {'code.py': 'import os\nimport sys\nimport numpy'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(self.scanner, '_get_packages_distributions', return_value={'numpy': ['numpy']}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertNotIn('os', result)
        self.assertNotIn('sys', result)
        self.assertIn('numpy', result)

    def test_local_imports_are_skipped_with_warning(self):
        files = {
            'local_mod.py': 'VALUE = 1',
            'main.py': 'import local_mod\nimport numpy',
        }
        create_test_python_project(self.temp_dir, files)

        with patch.object(self.scanner, '_get_packages_distributions', return_value={'numpy': ['numpy']}):
            result = self.scanner.scan_directory(self.temp_dir)

        self.assertIn('numpy', result)
        self.assertNotIn('local_mod', result)
        self.assertTrue(any("Skipped local import 'local_mod'" in warning for warning in self.scanner.warnings))

    def test_dynamic_import_non_literal_warns(self):
        files = {'main.py': 'name = "numpy"\nmodule = __import__(name)'}
        create_test_python_project(self.temp_dir, files)

        with patch.object(self.scanner, '_get_packages_distributions', return_value={}):
            self.scanner.scan_directory(self.temp_dir)

        self.assertTrue(any('Dynamic import skipped' in warning for warning in self.scanner.warnings))


if __name__ == '__main__':
    unittest.main()


"""Tests for CreateEnvCLI."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_env.cli import CreateEnvCLI, main
from .conftest import create_test_python_project, remove_test_dir


class TestCreateEnvCLI(unittest.TestCase):
    """Test cases for CreateEnvCLI."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cli = CreateEnvCLI()
        self.cli.scanner.USER_OVERRIDE_FILE_PATH = Path(self.temp_dir) / 'user_override.local.json'

    def tearDown(self):
        remove_test_dir(self.temp_dir)

    def test_parser_creation(self):
        parser = self.cli._create_parser()
        self.assertIsNotNone(parser)
        self.assertEqual(parser.prog, 'create_env')

    def test_parse_scan_command_basic(self):
        parser = self.cli._create_parser()
        args = parser.parse_args(['scan', '/path/to/project'])

        self.assertEqual(args.command, 'scan')
        self.assertEqual(args.project_path, '/path/to/project')
        self.assertIsNone(args.env_name)
        self.assertEqual(args.extra_index_url, [])

    def test_parse_scan_command_with_env_name(self):
        parser = self.cli._create_parser()
        args = parser.parse_args(['scan', '/path/to/project', '--env-name', 'myenv'])

        self.assertEqual(args.command, 'scan')
        self.assertEqual(args.project_path, '/path/to/project')
        self.assertEqual(args.env_name, 'myenv')

    def test_parse_scan_command_with_extra_index_urls(self):
        parser = self.cli._create_parser()
        args = parser.parse_args([
            'scan',
            '/path/to/project',
            '--extra-index-url',
            'https://download.pytorch.org/whl/cu126',
            '--extra-index-url',
            'https://example.com/simple',
        ])

        self.assertEqual(args.command, 'scan')
        self.assertEqual(
            args.extra_index_url,
            ['https://download.pytorch.org/whl/cu126', 'https://example.com/simple']
        )

    def test_run_with_no_command(self):
        with self.assertRaises(SystemExit) as cm:
            self.cli.run(['--help'])
        self.assertEqual(cm.exception.code, 0)

    def test_handle_scan_local_project(self):
        files = {'test.py': 'import numpy'}
        create_test_python_project(self.temp_dir, files)

        exit_code = self.cli.run(['scan', self.temp_dir])
        self.assertEqual(exit_code, 0)

        self.assertTrue((Path(self.temp_dir) / 'requirements.txt').exists())
        self.assertTrue((Path(self.temp_dir) / 'conda.yaml').exists())
        self.assertTrue((Path(self.temp_dir) / 'dependency_warnings.txt').exists())

    def test_main_function(self):
        files = {'test.py': 'import numpy'}
        create_test_python_project(self.temp_dir, files)

        exit_code = main(['scan', self.temp_dir])
        self.assertEqual(exit_code, 0)

    def test_main_function_scan_no_files(self):
        exit_code = main(['scan', self.temp_dir])
        self.assertEqual(exit_code, 0)

    def test_error_handling_invalid_directory(self):
        exit_code = self.cli.run(['scan', '/nonexistent/directory'])
        self.assertEqual(exit_code, 1)

    def test_declined_mapping_update_does_not_persist(self):
        files = {'test.py': 'import custom_unknown_lib'}
        create_test_python_project(self.temp_dir, files)

        mapping_file = Path(self.temp_dir) / '.create_env_mapping.local.json'
        self.cli.scanner.override_mapping_file_path = mapping_file
        self.cli.scanner.project_path = Path(self.temp_dir)
        self.cli.input_func = lambda _: 'n'

        with patch.object(self.cli.scanner, '_get_packages_distributions', return_value={}):
            exit_code = self.cli.run(['scan', self.temp_dir])

        self.assertEqual(exit_code, 0)
        self.assertFalse(mapping_file.exists())

    def test_approved_mapping_update_persists(self):
        files = {'test.py': 'import custom_unknown_lib'}
        create_test_python_project(self.temp_dir, files)

        mapping_file = Path(self.temp_dir) / '.create_env_mapping.local.json'
        self.cli.scanner.override_mapping_file_path = mapping_file
        self.cli.scanner.project_path = Path(self.temp_dir)
        self.cli.input_func = lambda _: 'y'

        with patch.object(self.cli.scanner, '_get_packages_distributions', return_value={}):
            exit_code = self.cli.run(['scan', self.temp_dir])

        self.assertEqual(exit_code, 0)
        self.assertTrue(mapping_file.exists())
        mapping_data = json.loads(mapping_file.read_text(encoding='utf-8'))
        self.assertIn('custom_unknown_lib', mapping_data)
        self.assertIsNone(mapping_data['custom_unknown_lib'])


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        remove_test_dir(self.temp_dir)

    def test_full_scan_workflow(self):
        files = {
            'main.py': 'import numpy\nfrom sklearn import datasets\nimport pandas as pd',
            'utils.py': 'import logging\nimport os',
            'image_processing.py': 'import cv2\nfrom PIL import Image',
        }
        create_test_python_project(self.temp_dir, files)

        cli = CreateEnvCLI()
        cli.scanner.USER_OVERRIDE_FILE_PATH = Path(self.temp_dir) / 'user_override.local.json'
        cli.input_func = lambda _: 'n'
        exit_code = cli.run(['scan', self.temp_dir])

        self.assertEqual(exit_code, 0)
        self.assertTrue((Path(self.temp_dir) / 'requirements.txt').exists())
        self.assertTrue((Path(self.temp_dir) / 'conda.yaml').exists())
        self.assertTrue((Path(self.temp_dir) / 'dependency_warnings.txt').exists())


if __name__ == '__main__':
    unittest.main()


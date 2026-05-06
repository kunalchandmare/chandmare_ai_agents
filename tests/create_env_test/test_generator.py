"""
Tests for ManifestGenerator.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_env.generator import ManifestGenerator
from .conftest import remove_test_dir


class TestManifestGenerator(unittest.TestCase):
    """Test cases for ManifestGenerator."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        remove_test_dir(self.temp_dir)

    def test_init_with_imports_and_warnings(self):
        resolved = {'numpy': 'numpy', 'pandas': 'pandas'}
        warnings = ['Warning 1', 'Warning 2']
        generator = ManifestGenerator(resolved, warnings)

        self.assertEqual(generator.resolved_imports, resolved)
        self.assertEqual(len(generator.warnings), 2)

    def test_generate_requirements_txt_with_versions(self):
        generator = ManifestGenerator({'numpy': 'numpy', 'pandas': 'pandas'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0', 'pandas': '1.3.0'}
        generator.generate_requirements_txt(self.temp_dir)

        content = (Path(self.temp_dir) / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('numpy==1.21.0', content)
        self.assertIn('pandas==1.3.0', content)

    def test_generate_requirements_txt_with_missing(self):
        generator = ManifestGenerator({'numpy': 'numpy'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0'}
        generator.missing_packages = ['unknown_package']
        generator.generate_requirements_txt(self.temp_dir)

        content = (Path(self.temp_dir) / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('numpy==1.21.0', content)
        self.assertIn('# unknown-package', content)

    def test_generate_conda_yaml_shape(self):
        generator = ManifestGenerator({'numpy': 'numpy', 'pandas': 'pandas'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0', 'pandas': '1.3.0'}
        generator.python_version = '3.12'
        generator.generate_conda_yaml(self.temp_dir, python_version='3.12')

        content = (Path(self.temp_dir) / 'conda.yaml').read_text(encoding='utf-8')
        self.assertIn('name: create-env-generated', content)
        self.assertIn('channels:', content)
        self.assertIn('  - conda-forge', content)
        self.assertIn('  - defaults', content)
        self.assertIn('dependencies:', content)
        self.assertIn('  - python=3.12', content)
        self.assertIn('  - pip', content)
        self.assertIn('  - pip:', content)
        self.assertIn('      - numpy==1.21.0', content)
        self.assertIn('      - pandas==1.3.0', content)

    def test_generate_conda_yaml_with_missing(self):
        generator = ManifestGenerator({'numpy': 'numpy'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0'}
        generator.missing_packages = ['unknown_package']
        generator.generate_conda_yaml(self.temp_dir)

        content = (Path(self.temp_dir) / 'conda.yaml').read_text(encoding='utf-8')
        self.assertIn('      - numpy==1.21.0', content)
        self.assertIn('      # - unknown-package', content)

    def test_generate_dependency_warnings_no_issues(self):
        generator = ManifestGenerator({}, [])
        generator.generate_dependency_warnings(self.temp_dir)

        content = (Path(self.temp_dir) / 'dependency_warnings.txt').read_text(encoding='utf-8')
        self.assertIn('No warnings or issues found', content)

    def test_generate_dependency_warnings_with_warnings(self):
        generator = ManifestGenerator({}, ['Warning 1', 'Warning 2'])
        generator.generate_dependency_warnings(self.temp_dir)

        content = (Path(self.temp_dir) / 'dependency_warnings.txt').read_text(encoding='utf-8')
        self.assertIn('Warnings:', content)
        self.assertIn('Warning 1', content)
        self.assertIn('Warning 2', content)

    def test_generate_dependency_warnings_with_missing_packages(self):
        generator = ManifestGenerator({}, [])
        generator.missing_packages = ['unknown', 'missing_pkg']
        generator.generate_dependency_warnings(self.temp_dir)

        content = (Path(self.temp_dir) / 'dependency_warnings.txt').read_text(encoding='utf-8')
        self.assertIn('Missing Packages:', content)
        self.assertIn('unknown', content)
        self.assertIn('missing-pkg', content)

    def test_generate_all_manifests(self):
        generator = ManifestGenerator({'numpy': 'numpy'}, ['Test warning'])
        generator.packages_with_versions = {'numpy': '1.21.0'}
        generator.missing_packages = ['unknown']
        generator.generate_all_manifests(self.temp_dir)

        self.assertTrue((Path(self.temp_dir) / 'requirements.txt').exists())
        self.assertTrue((Path(self.temp_dir) / 'conda.yaml').exists())
        self.assertTrue((Path(self.temp_dir) / 'dependency_warnings.txt').exists())

    def test_sorted_output(self):
        generator = ManifestGenerator({'zebra': 'zebra', 'apple': 'apple', 'middle': 'middle'}, [])
        generator.packages_with_versions = {'zebra': '1.0.0', 'apple': '1.0.0', 'middle': '1.0.0'}
        generator.generate_requirements_txt(self.temp_dir)

        lines = [
            line.strip() for line in (Path(self.temp_dir) / 'requirements.txt').read_text(encoding='utf-8').split('\n')
            if line.strip()
        ]
        self.assertEqual(lines[0], 'apple==1.0.0')
        self.assertEqual(lines[1], 'middle==1.0.0')
        self.assertEqual(lines[2], 'zebra==1.0.0')

    def test_normalized_output_package_names(self):
        generator = ManifestGenerator({'demo': 'My_Package.Name'}, [])
        generator.packages_with_versions = {'My_Package.Name': '1.0.0'}
        generator.missing_packages = ['Other_Package.Name']

        generator.generate_requirements_txt(self.temp_dir)
        generator.generate_conda_yaml(self.temp_dir)

        req_content = (Path(self.temp_dir) / 'requirements.txt').read_text(encoding='utf-8')
        conda_content = (Path(self.temp_dir) / 'conda.yaml').read_text(encoding='utf-8')

        self.assertIn('my-package-name==1.0.0', req_content)
        self.assertIn('# other-package-name', req_content)
        self.assertIn('      - my-package-name==1.0.0', conda_content)
        self.assertIn('      # - other-package-name', conda_content)

    def test_generate_requirements_txt_infers_torch_cuda_extra_index(self):
        generator = ManifestGenerator({'torch': 'torch', 'numpy': 'numpy'}, [])
        generator.packages_with_versions = {'torch': '2.9.0+cu126', 'numpy': '1.21.0'}
        generator.generate_all_manifests(self.temp_dir)

        content = (Path(self.temp_dir) / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('--index-url https://pypi.org/simple', content)
        self.assertIn('--extra-index-url https://download.pytorch.org/whl/cu126', content)
        self.assertIn('torch==2.9.0+cu126', content)

    def test_generate_requirements_warns_on_multiple_additional_websites(self):
        generator = ManifestGenerator({'torch': 'torch'}, [])
        generator.packages_with_versions = {'torch': '2.9.0+cu126'}
        generator.generate_all_manifests(
            self.temp_dir,
            additional_index_urls=['https://example.com/simple'],
        )

        self.assertTrue(any('Multiple additional package index websites detected' in warning for warning in generator.warnings))

    def test_python_version_resolved_from_environment(self):
        """Python version in conda.yaml must come from the resolved environment, not a hardcoded default."""
        generator = ManifestGenerator({'numpy': 'numpy'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0'}

        # Simulate resolve_versions setting python_version from the env
        with patch.object(generator, '_resolve_python_version', return_value='3.10') as mock_resolve:
            generator.python_version = mock_resolve.return_value
            generator.generate_all_manifests(self.temp_dir)

        content = (Path(self.temp_dir) / 'conda.yaml').read_text(encoding='utf-8')
        self.assertIn('  - python=3.10', content)
        self.assertNotIn('  - python=3.11', content)

    def test_python_version_fallback_to_active_interpreter(self):
        """When env resolution fails, Python version falls back to the active interpreter."""
        generator = ManifestGenerator({'numpy': 'numpy'}, [])
        generator.packages_with_versions = {'numpy': '1.21.0'}

        with patch('subprocess.run', side_effect=FileNotFoundError):
            generator.python_version = generator._resolve_python_version(env_name=None)

        expected_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        generator.generate_all_manifests(self.temp_dir)

        content = (Path(self.temp_dir) / 'conda.yaml').read_text(encoding='utf-8')
        self.assertIn(f'  - python={expected_version}', content)

    def test_resolve_versions_populates_python_version(self):
        """resolve_versions must set python_version on the generator instance."""
        generator = ManifestGenerator({'numpy': 'numpy'}, [])

        with patch.object(generator, '_get_package_version', return_value='1.21.0'), \
             patch.object(generator, '_resolve_python_version', return_value='3.9'):
            generator.resolve_versions()

        self.assertEqual(generator.python_version, '3.9')


if __name__ == '__main__':
    unittest.main()


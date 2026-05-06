"""Integration tests for package installability."""

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from .conftest import remove_test_dir


class TestCreateEnvInstallability(unittest.TestCase):
    """Validates that the create_env package can be installed in an isolated environment."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.venv_dir = Path(self.temp_dir) / "venv"
        self.project_root = Path(__file__).resolve().parents[2]
        self.package_dir = self.project_root / "packages" / "create_env"

    def tearDown(self):
        remove_test_dir(self.temp_dir)
        remove_test_dir(str(self.package_dir / 'build'))

    def _venv_python(self) -> Path:
        if sys.platform.startswith("win"):
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"

    def _expected_version(self) -> str:
        pyproject_path = self.package_dir / "pyproject.toml"
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        return pyproject_data["project"]["version"]

    def test_package_is_installable(self):
        create_venv = subprocess.run(
            [sys.executable, "-m", "venv", str(self.venv_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(create_venv.returncode, 0, msg=create_venv.stderr)

        venv_python = self._venv_python()
        self.assertTrue(venv_python.exists(), msg=f"Missing venv interpreter at {venv_python}")

        install_result = subprocess.run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(self.package_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(install_result.returncode, 0, msg=install_result.stderr)

        import_check = subprocess.run(
            [
                str(venv_python),
                "-c",
                "import create_env; import create_env.cli; print(create_env.__version__)",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(import_check.returncode, 0, msg=import_check.stderr)
        self.assertEqual(import_check.stdout.strip(), self._expected_version())

    def test_pip_install_with_extra_index_url_in_requirements(self):
        create_venv = subprocess.run(
            [sys.executable, '-m', 'venv', str(self.venv_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(create_venv.returncode, 0, msg=create_venv.stderr)

        venv_python = self._venv_python()
        self.assertTrue(venv_python.exists(), msg=f'Missing venv interpreter at {venv_python}')

        pip_version_result = subprocess.run(
            [str(venv_python), '-m', 'pip', '--version'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(pip_version_result.returncode, 0, msg=pip_version_result.stderr)
        pip_version = pip_version_result.stdout.split()[1]

        requirements_path = Path(self.temp_dir) / 'requirements.txt'
        requirements_path.write_text(
            '\n'.join([
                '--index-url https://pypi.org/simple',
                '--extra-index-url https://download.pytorch.org/whl/cu126',
                f'pip=={pip_version}',
                '',
            ]),
            encoding='utf-8',
        )

        install_result = subprocess.run(
            [
                str(venv_python),
                '-m',
                'pip',
                'install',
                '--disable-pip-version-check',
                '-r',
                str(requirements_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(install_result.returncode, 0, msg=install_result.stderr)


"""
ManifestGenerator - Generates requirements.txt, conda.yaml and dependency_warnings.txt.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class ManifestGenerator:
    """Generates deterministic dependency manifests."""

    def __init__(self, resolved_imports: Dict[str, str], warnings: List[str]):
        self.resolved_imports = resolved_imports
        self.warnings = warnings
        self.missing_packages: List[str] = []
        self.packages_with_versions: Dict[str, str] = {}

    @staticmethod
    def normalize_package_name(package_name: str) -> str:
        """Normalize package names before lookup and output."""
        return re.sub(r'[-_.]+', '-', package_name).lower()

    def resolve_versions(self, env_name: Optional[str] = None) -> None:
        """Resolve exact versions from conda (or pip fallback) for directly used packages."""
        for import_name, package_name in self.resolved_imports.items():
            normalized_name = self.normalize_package_name(package_name)
            version = self._get_package_version(normalized_name, env_name)

            if version:
                self.packages_with_versions[normalized_name] = version
            else:
                self.missing_packages.append(normalized_name)
                self.warnings.append(
                    f"Could not resolve version for package '{normalized_name}' (imported as '{import_name}')"
                )

    def _get_package_version(self, package_name: str, env_name: Optional[str] = None) -> Optional[str]:
        """Get package version from conda environment, with pip fallback."""
        try:
            if env_name:
                result = subprocess.run(
                    ['conda', 'list', '--json', '-n', env_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                result = subprocess.run(
                    ['conda', 'list', '--json'],
                    capture_output=True,
                    text=True,
                    check=True
                )

            packages = json.loads(result.stdout)
            for pkg in packages:
                if self.normalize_package_name(pkg['name']) == self.normalize_package_name(package_name):
                    return pkg['version']
            return None

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return self._get_pip_version(package_name)

    @staticmethod
    def _get_pip_version(package_name: str) -> Optional[str]:
        """Get package version using pip show."""
        try:
            result = subprocess.run(
                ['pip', 'show', package_name],
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split('Version:')[1].strip()
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def generate_requirements_txt(self, output_path: str) -> None:
        """Generate requirements.txt with directly used pinned packages only."""
        file_path = Path(output_path) / 'requirements.txt'
        normalized_versions = {
            self.normalize_package_name(package_name): version
            for package_name, version in self.packages_with_versions.items()
        }
        normalized_missing = sorted({self.normalize_package_name(name) for name in self.missing_packages})

        with open(file_path, 'w', encoding='utf-8') as file_obj:
            for package_name in sorted(normalized_versions.keys()):
                version = normalized_versions[package_name]
                file_obj.write(f"{package_name}=={version}\n")

            if normalized_missing:
                file_obj.write("\n# Missing packages (not found in environment):\n")
                for package_name in normalized_missing:
                    file_obj.write(f"# {package_name}\n")

    def generate_conda_yaml(
        self,
        output_path: str,
        environment_name: str = 'create-env-generated',
        python_version: str = '3.11'
    ) -> None:
        """Generate conda.yaml with python/pip and pinned direct deps under pip section."""
        file_path = Path(output_path) / 'conda.yaml'
        normalized_versions = {
            self.normalize_package_name(package_name): version
            for package_name, version in self.packages_with_versions.items()
        }
        normalized_missing = sorted({self.normalize_package_name(name) for name in self.missing_packages})

        with open(file_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(f"name: {environment_name}\n")
            file_obj.write("channels:\n")
            file_obj.write("  - conda-forge\n")
            file_obj.write("  - defaults\n")
            file_obj.write("dependencies:\n")
            file_obj.write(f"  - python={python_version}\n")
            file_obj.write("  - pip\n")
            file_obj.write("  - pip:\n")

            for package_name in sorted(normalized_versions.keys()):
                version = normalized_versions[package_name]
                file_obj.write(f"      - {package_name}=={version}\n")

            if normalized_missing:
                file_obj.write("\n      # Missing packages (not found in environment):\n")
                for package_name in normalized_missing:
                    file_obj.write(f"      # - {package_name}\n")

    def generate_dependency_warnings(self, output_path: str) -> None:
        """Generate dependency_warnings.txt."""
        file_path = Path(output_path) / 'dependency_warnings.txt'
        normalized_missing = sorted({self.normalize_package_name(name) for name in self.missing_packages})

        with open(file_path, 'w', encoding='utf-8') as file_obj:
            if not self.warnings and not normalized_missing:
                file_obj.write("No warnings or issues found.\n")
                return

            if self.warnings:
                file_obj.write("Warnings:\n")
                for warning in self.warnings:
                    file_obj.write(f"  - {warning}\n")

            if normalized_missing:
                file_obj.write("\nMissing Packages:\n")
                file_obj.write("The following packages were detected in imports but not found in the environment:\n")
                for package_name in normalized_missing:
                    file_obj.write(f"  - {package_name}\n")
                file_obj.write("\nPlease install these packages or update your environment.\n")

    def generate_all_manifests(
        self,
        output_path: str,
        environment_name: str = 'create-env-generated',
        python_version: str = '3.11'
    ) -> None:
        """Generate all manifest files in the output directory."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.generate_requirements_txt(str(output_dir))
        self.generate_conda_yaml(
            str(output_dir),
            environment_name=environment_name,
            python_version=python_version,
        )
        self.generate_dependency_warnings(str(output_dir))


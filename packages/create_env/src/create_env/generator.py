"""
ManifestGenerator - Generates requirements.txt, conda.yaml and dependency_warnings.txt.
"""

import json
import re
import subprocess
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, List, Optional, Set


class ManifestGenerator:
    """Generates deterministic dependency manifests."""

    PYPI_INDEX_URL = 'https://pypi.org/simple'
    TORCH_PACKAGE_NAMES = {'torch', 'torchvision', 'torchaudio'}
    TORCH_SUFFIX_PATTERN = re.compile(r'\+(?P<tag>cu\d+|cpu)$', re.IGNORECASE)

    def __init__(self, resolved_imports: Dict[str, str], warnings: List[str]):
        self.resolved_imports = resolved_imports
        self.warnings = warnings
        self.missing_packages: List[str] = []
        self.packages_with_versions: Dict[str, str] = {}
        self.additional_index_urls: List[str] = []
        self.python_version: Optional[str] = None

    @staticmethod
    def normalize_package_name(package_name: str) -> str:
        """Normalize package names before lookup and output."""
        return re.sub(r'[-_.]+', '-', package_name).lower()

    def resolve_versions(self, env_name: Optional[str] = None) -> None:
        """Resolve exact package versions and Python version from the target environment."""
        self.python_version = self._resolve_python_version(env_name)
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

    def _resolve_python_version(self, env_name: Optional[str] = None) -> str:
        """Resolve the Python major.minor version from the target conda env or active interpreter."""
        try:
            if env_name:
                result = subprocess.run(
                    ['conda', 'run', '-n', env_name, 'python', '--version'],
                    capture_output=True, text=True, check=True,
                )
            else:
                result = subprocess.run(
                    ['conda', 'run', 'python', '--version'],
                    capture_output=True, text=True, check=True,
                )
            version_str = (result.stdout or result.stderr).strip()
            # Output is like "Python 3.11.9"
            parts = version_str.split()
            if len(parts) >= 2:
                major_minor = '.'.join(parts[1].split('.')[:2])
                return major_minor
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback: use current interpreter
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}"

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

        effective_extra_index_urls = self._effective_additional_index_urls()

        with open(file_path, 'w', encoding='utf-8') as file_obj:
            if effective_extra_index_urls:
                file_obj.write(f"--index-url {self.PYPI_INDEX_URL}\n")
                for extra_url in effective_extra_index_urls:
                    file_obj.write(f"--extra-index-url {extra_url}\n")
                file_obj.write("\n")

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
        python_version: Optional[str] = None,
    ) -> None:
        """Generate conda.yaml with python/pip and pinned direct deps under pip section."""
        resolved_python = python_version or self.python_version or 'unknown'
        file_path = Path(output_path) / 'conda.yaml'
        normalized_versions = {
            self.normalize_package_name(package_name): version
            for package_name, version in self.packages_with_versions.items()
        }
        normalized_missing = sorted({self.normalize_package_name(name) for name in self.missing_packages})
        effective_extra_index_urls = self._effective_additional_index_urls()

        with open(file_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(f"name: {environment_name}\n")
            file_obj.write("channels:\n")
            file_obj.write("  - conda-forge\n")
            file_obj.write("  - defaults\n")
            file_obj.write("dependencies:\n")
            file_obj.write(f"  - python={resolved_python}\n")
            file_obj.write("  - pip\n")
            file_obj.write("  - pip:\n")

            if effective_extra_index_urls:
                file_obj.write(f"      - --index-url {self.PYPI_INDEX_URL}\n")
                for extra_url in effective_extra_index_urls:
                    file_obj.write(f"      - --extra-index-url {extra_url}\n")

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
        python_version: Optional[str] = None,
        additional_index_urls: Optional[List[str]] = None,
    ) -> None:
        """Generate all manifest files in the output directory."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.additional_index_urls = additional_index_urls or []
        resolved_python = python_version or self.python_version

        self.generate_requirements_txt(str(output_dir))
        self.generate_conda_yaml(
            str(output_dir),
            environment_name=environment_name,
            python_version=resolved_python,
        )
        self.generate_dependency_warnings(str(output_dir))

    def _effective_additional_index_urls(self) -> List[str]:
        """Return deterministic extra index URLs from user input and inferred package rules."""
        combined_urls: Set[str] = set(url.strip() for url in self.additional_index_urls if url and url.strip())
        combined_urls.update(self._infer_additional_index_urls_from_versions())

        ordered_urls = sorted(combined_urls)
        self._warn_if_multiple_hosts(ordered_urls)
        return ordered_urls

    def _infer_additional_index_urls_from_versions(self) -> Set[str]:
        """Infer additional indexes from package versions (e.g., torch CUDA/CPU wheels)."""
        inferred_urls: Set[str] = set()

        for package_name, version in self.packages_with_versions.items():
            normalized_package = self.normalize_package_name(package_name)
            if normalized_package not in self.TORCH_PACKAGE_NAMES:
                continue

            suffix_match = self.TORCH_SUFFIX_PATTERN.search(version.strip())
            if not suffix_match:
                continue

            tag = suffix_match.group('tag').lower()
            inferred_urls.add(f"https://download.pytorch.org/whl/{tag}")

        return inferred_urls

    def _warn_if_multiple_hosts(self, urls: List[str]) -> None:
        """Warn when requirements need more than one additional package index website."""
        hosts = {urlparse(url).netloc for url in urls if urlparse(url).netloc}
        if len(hosts) > 1:
            self.warnings.append(
                "Multiple additional package index websites detected: "
                + ", ".join(sorted(hosts))
                + ". pip will search across all configured indexes; consider split install commands for strict control."
            )


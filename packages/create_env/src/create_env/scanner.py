"""
DependencyScanner - Recursively scans Python files and identifies dependencies.
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from importlib import metadata as importlib_metadata


class DependencyScanner:
    """Scans local Python source files to identify external dependencies."""

    STDLIB_MODULES = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
        'abc', 'argparse', 'ast', 'asyncio', 'collections', 'copy', 'dataclasses',
        'datetime', 'enum', 'functools', 'glob', 'io', 'itertools', 'json', 'logging',
        'math', 'os', 'pathlib', 'pickle', 'random', 're', 'shutil', 'subprocess',
        'sys', 'tempfile', 'threading', 'time', 'typing', 'unittest', 'warnings',
        'builtins', '__builtin__', '__builtins__', 'urllib', 'http', 'ssl', 'socket',
        'importlib',
    }

    DEFAULT_IMPORT_MAPPING = {
        'sklearn': 'scikit-learn',
        'cv2': 'opencv-python',
        'yaml': 'pyyaml',
        'PIL': 'Pillow',
        'bs4': 'beautifulsoup4',
    }

    PACKAGED_MAPPING_FILE_NAME = 'package_name_mapping.json'
    PROJECT_OVERRIDE_FILE_NAME = '.create_env_mapping.local.json'
    USER_OVERRIDE_FILE_PATH = Path.home() / '.create_env' / 'package_name_mapping.local.json'

    IMPORT_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
    PACKAGE_NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')

    def __init__(self):
        self.found_imports: Set[str] = set()
        self.warnings: List[str] = []
        self.pending_mapping_updates: Dict[str, Optional[str]] = {}
        self.project_path: Optional[Path] = None
        self.local_project_modules: Set[str] = set()
        self.packaged_mapping_file_path = Path(__file__).with_name(self.PACKAGED_MAPPING_FILE_NAME)
        self.override_mapping_file_path: Optional[Path] = None

    def configure_mapping_paths(self, project_path: Path) -> None:
        """Configure local override mapping file paths for this run."""
        self.project_path = project_path
        self.override_mapping_file_path = project_path / self.PROJECT_OVERRIDE_FILE_NAME

    def get_default_override_mapping_path(self) -> Path:
        """Return the writable local override mapping path used when persisting unresolved imports."""
        if self.project_path:
            return self.project_path / self.PROJECT_OVERRIDE_FILE_NAME
        if self.override_mapping_file_path:
            return self.override_mapping_file_path
        return self.USER_OVERRIDE_FILE_PATH

    def scan_directory(self, directory: str) -> Dict[str, str]:
        """Recursively scan a local directory for Python files and extract dependencies."""
        self.found_imports.clear()
        self.warnings.clear()
        self.pending_mapping_updates.clear()

        project_path = Path(directory)
        if not project_path.exists():
            raise FileNotFoundError(f"Directory not found: {project_path}")

        self.configure_mapping_paths(project_path)
        self.local_project_modules = self._discover_local_project_modules(project_path)

        py_files = list(project_path.rglob('*.py'))
        if not py_files:
            self.warnings.append(f"No Python files found in {project_path}")

        for py_file in py_files:
            self._scan_file(py_file)

        return self._resolve_imports()

    def _discover_local_project_modules(self, project_path: Path) -> Set[str]:
        """Discover top-level local modules/packages so they can be skipped as local imports."""
        modules: Set[str] = set()

        for child in project_path.iterdir():
            if child.is_file() and child.suffix == '.py' and child.stem != '__init__':
                modules.add(child.stem)
            elif child.is_dir() and (child / '__init__.py').exists():
                modules.add(child.name)

        return modules

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single Python file for imports using AST."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._process_import(alias.name, is_dynamic=False)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._process_import(node.module, is_dynamic=False)
                elif isinstance(node, ast.Call):
                    self._process_dynamic_import(node, file_path)

        except SyntaxError as exc:
            self.warnings.append(f"Syntax error in {file_path}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive guard
            self.warnings.append(f"Error scanning {file_path}: {exc}")

    def _process_dynamic_import(self, node: ast.Call, file_path: Path) -> None:
        """Detect and handle dynamic imports from __import__ / importlib.import_module."""
        dynamic_target = None

        if isinstance(node.func, ast.Name) and node.func.id == '__import__':
            dynamic_target = '__import__'
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == 'import_module'
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == 'importlib'
        ):
            dynamic_target = 'importlib.import_module'

        if not dynamic_target:
            return

        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            self._process_import(node.args[0].value, is_dynamic=True)
            return

        self.warnings.append(
            f"Dynamic import skipped in {file_path} at line {getattr(node, 'lineno', '?')}: "
            f"{dynamic_target}(...) argument is not a static string literal."
        )

    def _process_import(self, import_name: str, is_dynamic: bool) -> None:
        """Process import and track dependency candidates while skipping local/stdlib imports."""
        root_module = import_name.split('.')[0]

        if root_module in self.STDLIB_MODULES or root_module.startswith('_'):
            return

        if root_module in self.local_project_modules:
            self.warnings.append(
                f"Skipped local import '{root_module}'"
                + (" (dynamic)" if is_dynamic else "")
                + "."
            )
            return

        self.found_imports.add(root_module)

    def _resolve_imports(self) -> Dict[str, str]:
        """Resolve imports to normalized distribution package names."""
        resolved: Dict[str, str] = {}

        import_to_distributions = self._get_packages_distributions()
        packaged_mapping = self._load_packaged_fallback_mapping()
        override_mapping = self._load_local_override_mapping()

        for import_name in sorted(self.found_imports):
            candidates = self._get_distribution_candidates(import_to_distributions, import_name)
            if len(candidates) == 1:
                resolved[import_name] = candidates[0]
                continue
            if len(candidates) > 1:
                self.warnings.append(
                    f"Ambiguous distribution mapping for import '{import_name}': [{', '.join(candidates)}]. "
                    "No package selected."
                )
                continue

            override_mapped = self._lookup_mapping(override_mapping, import_name)
            if override_mapped:
                resolved[import_name] = self.normalize_package_name(override_mapped)
                continue

            fallback_mapped = self._lookup_mapping(packaged_mapping, import_name)
            if fallback_mapped:
                resolved[import_name] = self.normalize_package_name(fallback_mapped)
                continue

            self.warnings.append(
                f"Unresolved import '{import_name}'. Add a mapping in local override file at "
                f"{self.get_default_override_mapping_path()}."
            )
            if import_name not in override_mapping:
                self.pending_mapping_updates[import_name] = None

        return resolved

    @staticmethod
    def _lookup_mapping(mapping: Dict[str, Optional[str]], import_name: str) -> Optional[str]:
        """Lookup import mapping using exact and lowercase keys."""
        mapped = mapping.get(import_name)
        if mapped is None:
            mapped = mapping.get(import_name.lower())
        return mapped

    def persist_pending_mapping_updates(self) -> bool:
        """Persist queued unresolved imports to the local override file after approval."""
        if not self.pending_mapping_updates:
            return False

        override_path = self.get_default_override_mapping_path()
        override_mapping = self._load_mapping_file(override_path, source_label='local override')
        mapping_updated = False

        for import_name, mapped_name in sorted(self.pending_mapping_updates.items()):
            if import_name not in override_mapping:
                override_mapping[import_name] = mapped_name
                mapping_updated = True

        if mapping_updated:
            self._save_mapping_file(override_path, override_mapping)

        self.pending_mapping_updates.clear()
        return mapping_updated

    @staticmethod
    def normalize_package_name(package_name: str) -> str:
        """Normalize package names using canonical distribution style."""
        return re.sub(r'[-_.]+', '-', package_name).lower()

    @staticmethod
    def _get_packages_distributions() -> Dict[str, List[str]]:
        """Wrapper for importlib metadata lookup to simplify testing."""
        return importlib_metadata.packages_distributions() or {}

    def _load_packaged_fallback_mapping(self) -> Dict[str, Optional[str]]:
        """Load packaged fallback mapping (read-only at runtime)."""
        if not self.packaged_mapping_file_path.exists():
            # Keep defaults in-memory if packaged file is missing.
            return dict(self.DEFAULT_IMPORT_MAPPING)

        loaded = self._load_mapping_file(self.packaged_mapping_file_path, source_label='packaged fallback')
        merged = dict(self.DEFAULT_IMPORT_MAPPING)
        merged.update(loaded)
        return merged

    def _load_local_override_mapping(self) -> Dict[str, Optional[str]]:
        """Load optional local override mappings from user and project paths."""
        merged: Dict[str, Optional[str]] = {}

        if self.USER_OVERRIDE_FILE_PATH.exists():
            merged.update(self._load_mapping_file(self.USER_OVERRIDE_FILE_PATH, source_label='local override'))

        project_override = self.get_default_override_mapping_path()
        if project_override.exists():
            # Project-level mapping overrides user-level mapping.
            merged.update(self._load_mapping_file(project_override, source_label='local override'))

        return merged

    def _load_mapping_file(self, path: Path, source_label: str) -> Dict[str, Optional[str]]:
        """Load and validate a JSON mapping file."""
        try:
            raw_data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            self.warnings.append(f"Failed to load {source_label} mapping from {path}: {exc}")
            return {}

        if not isinstance(raw_data, dict):
            self.warnings.append(f"Ignored {source_label} mapping in {path}: root JSON value must be an object.")
            return {}

        validated: Dict[str, Optional[str]] = {}
        for key, value in raw_data.items():
            key_ok, value_ok = self._validate_mapping_entry(key, value)
            if not key_ok:
                self.warnings.append(
                    f"Ignored malformed mapping key '{key}' in {source_label} mapping file {path}."
                )
                continue
            if not value_ok:
                self.warnings.append(
                    f"Ignored malformed mapping value for key '{key}' in {source_label} mapping file {path}."
                )
                continue
            validated[key] = value

        return validated

    def _validate_mapping_entry(self, key: object, value: object) -> Tuple[bool, bool]:
        """Validate mapping key/value rules required by the specification."""
        if not isinstance(key, str) or not self.IMPORT_NAME_PATTERN.match(key):
            return False, False

        if value is None:
            return True, True

        if not isinstance(value, str):
            return True, False

        stripped = value.strip()
        if not stripped:
            return True, False

        return True, bool(self.PACKAGE_NAME_PATTERN.match(stripped))

    def _save_mapping_file(self, path: Path, mapping: Dict[str, Optional[str]]) -> None:
        """Write local override mapping JSON file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        except OSError as exc:
            self.warnings.append(f"Failed to write local override mapping file {path}: {exc}")

    def _get_distribution_candidates(self, mapping: Dict[str, List[str]], import_name: str) -> List[str]:
        """Get deterministic normalized distribution candidates for an import."""
        raw_candidates = mapping.get(import_name)
        if raw_candidates is None:
            raw_candidates = mapping.get(import_name.lower(), [])

        return sorted(
            {
                self.normalize_package_name(candidate)
                for candidate in raw_candidates
                if isinstance(candidate, str) and candidate.strip()
            }
        )


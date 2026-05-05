# create_env_agent specification

**Author:** Chandmare, Kunal  
**Model:** GPT-4  
**Created:** 2026-05-05

`create_env_agent` scans local Python source files with AST and creates deterministic dependency manifests for reproducible local setup and execution.

## Command

```bash
python -m create_env scan <project_path>
python -m create_env scan <project_path> --env-name <conda_env_name>
```

## Options

- `<project_path>`: Local path to scan recursively (required)
- `--env-name <conda_env_name>`: Resolve exact package versions from a specific local conda environment instead of the active Python environment

## Scope

`create_env_agent` is a fully local solution.

It does not:
- clone remote repositories
- push updates to remote repositories
- create commits automatically
- update shared canonical mappings at runtime

All scanning, resolution, file generation, and optional mapping updates happen locally on the user machine.

## Guarantees

- uses folder_structure_agent.md for maintaining folder structure , use agent_name = "create_env"
- **Package must include both `pyproject.toml` and `setup.py`** for full installability. These files must be placed at the package root (`packages/create_env/`), not under `src/`. The `pyproject.toml` defines modern build metadata while `setup.py` ensures compatibility with legacy tools.
- **Package author in `setup.py` must match the agent author** (`Chandmare, Kunal`). This ensures consistent attribution across all package metadata and documentation.
- Scans `.py` files recursively under the given local `<project_path>`.
- Ignores Python standard library modules and local project imports.
- Uses `importlib.metadata.packages_distributions()` as the primary import-to-distribution mapping source.
- Uses packaged fallback mapping data only when metadata mapping fails.
- Supports known fallback remappings such as:
  - `sklearn` -> `scikit-learn`
  - `cv2` -> `opencv-python`
  - `yaml` -> `pyyaml`
  - `PIL` -> `Pillow`
  - `bs4` -> `beautifulsoup4`
- If multiple distributions are returned for one import, writes a warning and does not silently choose one.
- Resolves exact installed versions for used packages only.
- Normalizes final package names before writing output manifests.
- Can resolve versions from a specific local conda environment via `--env-name`.
- Generates output files in the scanned `<project_path>`:
  - `requirements.txt`
  - `conda.yaml`
  - `dependency_warnings.txt`
- Organizes implementation under `packages/create_env/src/create_env/` with supporting files at package root (`pyproject.toml`, `setup.py`, `README.md`) and tests under `tests/create_env_test/`.

## Mapping policy

`create_env_agent` uses a layered local mapping strategy:

1. Installed environment metadata mapping
2. Optional local user override mapping file
3. Packaged fallback mapping file
4. Warning output for unresolved imports

### Packaged fallback mapping

The package includes a curated fallback mapping file shipped with the installed package, for example:

```text
packages/create_env/src/create_env/data/package_name_mapping.json
```

This packaged JSON is read-only at runtime and is updated only through source control and package releases.

### Local override mapping

Users may optionally maintain a local override mapping file, for example:

```text
<project_path>/.create_env_mapping.local.json
```

or a user-level local file such as:

```text
~/.create_env/package_name_mapping.local.json
```

The local override file is used only on the current machine and takes precedence over the packaged fallback mapping.

### Unresolved imports

If an import cannot be resolved, the agent:
- records it in `dependency_warnings.txt`
- may ask user permission to write the unresolved import into the local override mapping file with a `null` value placeholder
- never mutates the packaged canonical mapping JSON at runtime

This keeps package defaults stable while still allowing local learning and future correction.

## Output rules

### requirements.txt

- Contains only directly used third-party packages detected from the scanned codebase
- Uses exact installed versions from the chosen local environment
- Excludes unrelated installed packages
- Excludes transitive dependencies not directly imported by the project

### conda.yaml

- Is generated from the same resolved package set
- Includes a local environment name
- Includes `python` and `pip` in conda dependencies
- Places resolved pinned packages under the `pip:` section unless future conda-channel resolution is explicitly added

Example shape:

```yaml
name: create-env-generated
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
      - mlflow==2.14.1
      - pandas==2.2.2
      - scikit-learn==1.5.1
```

### dependency_warnings.txt

Contains:
- unresolved imports
- ambiguous mappings
- imports missing from the selected environment
- imports skipped because they appear local or dynamic

## Validation rules

Any mapping loaded from packaged fallback JSON or local override JSON must be validated:

- import key must be a valid top-level Python import-like name
- package value must be either `null` or a valid distribution-like package name
- empty strings are rejected
- malformed entries are ignored and reported in warnings

## Versioning

- The package is installable and versioned starting from `0.0.1`
- Mapping improvements in the packaged fallback JSON are released through normal package version updates
- Local override mappings are not considered part of the package version

## Repository layout

Recommended structure:

```text
chandmare_ai_agents/
  agents/
    create_env_agent.md
  packages/
    create_env/
      pyproject.toml
      src/
        create_env/
          __init__.py
          __main__.py
          cli.py
          scanner.py
          mapper.py
          versions.py
          writer.py
          data/
            package_name_mapping.json
  tests/
    create_env_test/
      test_scanner.py
      test_mapper.py
      test_versions.py
      test_mapping_data.py
```

## Design principles

- Local-first
- Deterministic
- Minimal pinned dependencies only
- Stable packaged defaults
- Safe local extensibility through override files
- No automatic remote mutation
# create_env

**Author:** Chandmare, Kunal  
**Model:** GPT-4  
**Created:** 2026-05-05

`create_env` scans local Python source files using AST and creates deterministic dependency manifests for reproducible local setup.

## Features

- Recursive scan of `.py` files under a local project path
- Ignores Python stdlib imports and local project imports
- Layered mapping strategy:
  1. `importlib.metadata.packages_distributions()`
  2. local override mapping file (if present)
  3. packaged fallback mapping data
- Deterministic ambiguity handling (warns and skips when multiple distributions exist)
- Optional permission-based update of local override mapping with unresolved imports
- Exact version pinning for directly used packages only
- Normalized package names in outputs

## Installation

```bash
pip install -e /path/to/packages/create_env
```

## Usage

### Scan local project

```bash
python -m create_env scan /path/to/project
```

### Scan with specific local conda environment

```bash
python -m create_env scan /path/to/project --env-name myenv
```

## Mapping files

### Packaged fallback (read-only at runtime)

- `packages/create_env/package_name_mapping.json`

### Local override (optional)

- Project-local preferred: `<project_path>/.create_env_mapping.local.json`
- User-level fallback: `~/.create_env/package_name_mapping.local.json`

If unresolved imports are found, the CLI can ask permission to add `null` placeholders into the local override mapping file.

## Output files

Generated in the scanned `<project_path>`:

- `requirements.txt`
- `conda.yaml`
- `dependency_warnings.txt`

### `conda.yaml` shape

`conda.yaml` includes:

- environment name
- channels (`conda-forge`, `defaults`)
- `python` and `pip` in conda dependencies
- pinned direct packages under `pip:` section

## Version

1.0.0 (Stable)

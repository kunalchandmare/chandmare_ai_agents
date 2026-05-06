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

### Command

```bash
python -m create_env scan <project_path> [OPTIONS]
```

### Arguments

| Argument | Description |
|---|---|
| `project_path` | Local path to scan recursively (required) |

### Options

| Option | Description |
|---|---|
| `--env-name <name>` | Resolve versions from a specific local conda environment instead of the active one |
| `--extra-index-url <url>` | Additional pip package index URL. PyPI remains the default index. Can be provided multiple times. |

### Examples

#### Scan local project

```bash
python -m create_env scan /path/to/project
```

#### Scan with a specific conda environment

```bash
python -m create_env scan /path/to/project --env-name myenv
```

#### Scan with a custom extra package index (e.g. PyTorch CUDA wheels)

```bash
python -m create_env scan /path/to/project --extra-index-url https://download.pytorch.org/whl/cu126
```

#### Scan with multiple extra indexes

```bash
python -m create_env scan /path/to/project \
  --extra-index-url https://download.pytorch.org/whl/cu126 \
  --extra-index-url https://my-private-index.example.com/simple
```

> **Note:** When multiple additional package index websites are detected, a warning is written to `dependency_warnings.txt` recommending split install commands for strict package source control.

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

# mlflow-pipeline-template

Generates a fully structured MLflow + Hydra pipeline project from two user-provided YAML files.

---

## Installation

```bash
pip install -e /path/to/packages/mlflow_pipeline_template
pip uninstall chandmare-mlflow-pipeline-template  # uninstall any previous version
```

---

## How it works

1. Run: `mlflow-pipeline-template generate <project_path>` — creates `config.yaml.sample` and `pipeline.yaml.sample` in the project folder
2. User renames them to `.yaml` and edits for their project
3. Run: `mlflow-pipeline-template generate <project_path> --config <path> --pipeline <path>` — generates the full ML pipeline
4. Generated Python files are compile-checked during generation so template indentation/syntax issues fail fast.

**Init mode (no --config/--pipeline):** creates `.yaml.sample` files as reference for user to edit  
**Generate mode (with --config and --pipeline):** parses `.yaml` files and generates the full project structure

---

## Usage

```bash
# 1. Init mode: generate sample files (.yaml.sample)
mlflow-pipeline-template generate ./my_project

# 2. Rename and edit: config.yaml.sample → config.yaml, pipeline.yaml.sample → pipeline.yaml

# 3. Generate mode: build full pipeline from edited files (must have .yaml extension)
mlflow-pipeline-template generate ./my_project --config ./my_project/config.yaml --pipeline ./my_project/pipeline.yaml

# 4. Implement your logic in each run.py
# 5. Run the pipeline
cd my_project
mlflow run . -P steps=all

# Clean: remove all generated artifacts
mlflow-pipeline-template clean ./my_project

# Clean but keep selected working steps/components (multiple names allowed)
mlflow-pipeline-template clean ./my_project --keep download split
mlflow-pipeline-template clean ./my_project --keep download test_model
mlflow-pipeline-template clean ./my_project --keep download split test_model
```

## `config.yaml` — Parameter Reference

Project-level infrastructure configuration.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_name` | str | **yes** | — | Project name. Used as MLflow project name and folder name. |
| `project_slug` | str | no | auto from `project_name` | Python-safe slug. Auto-derived as lowercase with underscores. Override if needed. |
| `tracking_backend` | str | no | "mlflow" | Experiment tracking backend. One of: `mlflow`, `wandb`. |
| `artifact_backend` | str | no | "dvc" | Artifact storage/versioning backend. Currently `dvc` only; wandb is not a valid artifact backend. |
| `mlflow_version` | str | no | `"2.14.1"` | MLflow version pinned in the project. |
| `wandb_entity` | str | only if `wandb` | — | W&B entity (username or team). Required when `tracking_backend: wandb`. |
| `wandb_project` | str | only if `wandb` | same as `project_name` | W&B project name. Required when `tracking_backend: wandb`. |
| `wandb_version` | str | only if `wandb` | "0.17.0" | W&B SDK version. |
| `dvc_remote` | str | only if `dvc` | `""` | DVC remote URL (e.g. `s3://bucket/path`). Leave empty to configure later. |

### Backend choices

- `tracking_backend`: `mlflow` (default) or `wandb`
- `artifact_backend`: `dvc` (default); wandb is not supported as an artifact backend
- Even when `tracking_backend` is `wandb`, the generated project still uses MLflow for orchestration in `main.py`.

---

## `pipeline.yaml` — Parameter Reference

Pipeline shape definition. Defines what steps and components exist plus their argument interfaces.

### Top-level structure

```yaml
steps:
  <step_name>:
    description: "..."
    arguments:
      <arg_name>: { type, default, required, description }

components:
  <component_name>:
    description: "..."
    arguments:
      <arg_name>: { type, default, required, description }
```

### Step/Component fields

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | str | no | Human-readable description of what this step/component does |
| `arguments` | dict | no | Map of argument names to their schemas (see below) |

### Argument schema

Each argument under `arguments:` has the following fields:

| Field        | Type | Required | Default | Description |
|---           |---   |---       |---      |---|
| `type`       | str  | **yes**  | —       | Python type: `str`, `int`, `float`, `bool` |
| `default`    | any  | no       | —       | Default value. If omitted, argument has no default. |
| `required`   | bool | no       | `false` | If `true`, argument must be provided at runtime (no default). |
| `description`| str  | always   | `""`   | Help text for argparse and documentation. Always present; defaults to empty string if not provided. |

> **Note:** The `description` field is always present for every argument (including multiplicity sets and sub-arguments). If not provided in your YAML, it will default to an empty string (`""`).

### Boolean arguments

Boolean arguments are handled as **explicit values end-to-end**, not as presence-only flags.

- In `params.yaml`, booleans appear as YAML values: `true` / `false`
- In generated `main.py`, they are forwarded to `mlflow.run()` as explicit string values
- In generated `MLproject`, they are exposed as normal parameters
- In generated `run.py`, they are parsed from explicit values such as `--force_download true` or `--force_download false`

This also applies to multiplicity sub-arguments such as `dataset_sources[].force_download`.

### How arguments propagate

Arguments defined in `pipeline.yaml` automatically generate:

| Generated file | What's produced |
|---|---|
| `run.py` | `argparse.add_argument("--<arg_name>", type=<type>, ...)` |
| `MLproject` | `parameters: <arg_name>: { type, default, description }` |
| `config.yaml` (in generated project) | Section per step with argument keys for runtime values |

The orchestrator also injects an internal `run_name` parameter into each child `mlflow.run(...)` call. You do **not** define `run_name` in `pipeline.yaml`; it is generated automatically from the experiment name and a short UUID suffix so all child step/component runs can be grouped together.

### MLflow tracking configuration and run grouping

Generated projects include `shared/mlflow_utils.py`, and both root `main.py` and each generated step/component `run.py` call `configure_project_mlflow(PROJECT_ROOT)`. This keeps MLflow tracking configuration consistent across the root orchestrator and child MLflow Projects.

By default, local tracking uses a project-root SQLite tracking database (`mlflow.db`) through a Windows-safe URI. The root `main.py` resolves `main.experiment_name`, creates a pipeline group id in the form `<experiment_name>-<last_4_uuid_hex>`, and passes it to children as the internal `run_name` parameter. Generated `run.py` files use that value as the MLflow run name and also tag it as `pipeline_group_id`.

### Nullable defaults (`default: null`)

For nullable arguments (for example `type: float` with `default: null`), generation keeps values safe across MLflow and argparse:

- In generated `MLproject`, nullable numeric parameters are emitted as `type: string` with `default: ""` for transport safety.
- In generated root `main.py`, `None` is serialized as an empty string before calling `mlflow.run(...)`.
- In generated `run.py`, optional parsers convert `""`, `null`, or `none` back to Python `None` (and parse real numbers normally).

### `params.yaml` examples

The generated `params.yaml` is the runtime configuration consumed by Hydra in `main.py`.

**Standard example:**

```yaml
main:
  steps: all
  experiment_name: dev
  project_name: image_classifier
  tracking_backend: wandb
  artifact_backend: dvc
  wandb_entity: myteam

download:
  source_url: ""
  output_artifact: ""

split:
  input_artifact: ""
  test_size: 0.2
  random_seed: 42

training:
  train_artifact: ""
  epochs: 10
  learning_rate: 0.001
```

Notes:
- `main.steps: all` runs the full pipeline.
- Required arguments without defaults are initialized as empty strings for you to fill in.
- Optional arguments are pre-populated from defaults defined in `pipeline.yaml`.

**Multiplicity example (`dataset_sources`):**

```yaml
main:
  steps: download
  experiment_name: dev
  project_name: robotathome_download

download:
  dataset_sources:
    - out_dir: "C:\\Users\\fixc9dv\\Downloads"
      extract_root: data
      force_download: false
      dataset_url: "https://zenodo.org/record/7811795/files/Robot@Home2_db.tgz"
      dataset_filename: "Robot@Home2_db.tgz"
      dataset_md5: "d34fb44c01f31c87be8ab14e5ecd0767"
      dataset_extract_to: data
    - out_dir: "C:\\Users\\fixc9dv\\Downloads"
      extract_root: data
      force_download: true
      dataset_url: "https://zenodo.org/record/7811795/files/Robot@Home2_rgbd.tgz"
      dataset_filename: "Robot@Home2_rgbd.tgz"
      dataset_md5: "abcdef1234567890"
      dataset_extract_to: data
```

Notes:
- Each item in `dataset_sources` is one entry in the multiplicity set.
- Boolean values such as `force_download` stay value-based in `params.yaml` as `true` / `false`.
- If an optional multiplicity sub-argument is omitted, generated `main.py` falls back to the default from `pipeline.yaml`.

---

## `steps:` vs `components:` — When to use which

### `steps:` — Project-Specific Logic (`src/`)

Steps contain **your domain logic**. They know about your specific data, model, and business rules.

| Property | Detail |
|---|---|
| Generated to | `src/<step_name>/` |
| Knows schema | ✅ Yes — column names, data types, business thresholds |
| Reusable | ❌ No — tied to this project's data and logic |
| Examples | `clean` (filters price 10-350), `train` (Random Forest with specific hyperparams), `feature_eng` (creates `price_per_sqft`) |

**Put it in `steps:` when:**
- It references specific column names
- It applies business rules or thresholds
- It chooses model architecture or hyperparameters
- It performs domain-specific feature engineering

### `components:` — Reusable, Schema-Agnostic Blocks (`components/`)

Components are **generic building blocks** that work with ANY project without modification.

| Property | Detail |
|---|---|
| Generated to | `components/<component_name>/` |
| Knows schema | ❌ No — operates on artifacts as opaque files |
| Reusable | ✅ Yes — can be shared across teams and projects |
| Examples | `download_data` (fetch any artifact), `train_val_test_split` (split any DataFrame by row), `test_model` (run predict on any model + test set) |

**Put it in `components:` when:**
- It moves, splits, downloads, or uploads artifacts without knowing their content
- It works with any column structure
- It could be extracted to a shared repository and reused across projects
- It has no hardcoded column names, thresholds, or model choices

### Decision flowchart

```
Does this step need to know column names, business thresholds, or model details?
├── YES → define under steps: (goes to src/)
└── NO  → define under components: (goes to components/)
```

---

## Multiplicity Argument Sets

You can define a set of arguments as a list using the `multiplicity` feature **in your `pipeline.yaml` under the `arguments` section**. This is useful when you want to specify a repeated group of arguments (e.g., multiple input sources, repeated parameter blocks, etc.).

**pipeline.yaml Example:**

```yaml
steps:
  my_step:
    description: "Step with repeated argument set"
    arguments:
      my_arg_set:
        multiplicity: true
        multiplicity_count: 3
        args:
          - arg1:
              type: str
              default: foo
              required: true
              description: "First argument in set."
            arg2:
              type: int
              default: 42
              description: "Second argument in set."
```

- Only the parent group (`my_arg_set`) is named.
- `multiplicity: true` enables the feature.
- `multiplicity_count` sets the number of repeated sets.
- `args` is a list of argument definitions (each entry is a dict of argument names and their schemas).

**params.yaml Example (result):**

```yaml
my_step:
  my_arg_set:
    - arg1: foo1  # User can edit each set individually
      arg2: 42
    - arg1: foo2
      arg2: 99
    - arg1: bar
      arg2: 123
```

- In `params.yaml`, the multiplicity argument appears as a list of dicts, each with the specified defaults (users can edit each set as needed).
- The generated code and MLproject will reflect this structure for runtime use (the parent argument is passed as a single grouped parameter).

---

## Generated project structure

```
<project_name>/
├── main.py                          # Hydra pipeline orchestrator
├── MLproject                        # root MLflow entry point
├── config.yaml                      # runtime values for step arguments
├── pipeline.yaml                    # pipeline definition (copied from input)
├── conda.yml                        # (required, not generated by this agent; typically created by user, recommended: create_env_agent)
├── shared/                          # shared utilities used across steps/components
│   ├── __init__.py
│   ├── helpers.py                   # generated parser helpers imported by each run.py
│   └── mlflow_utils.py              # generated shared MLflow tracking configuration helpers
│
├── components/                      # reusable blocks
│   └── <component_name>/
│       ├── run.py                   # argparse from pipeline.yaml arguments
│       ├── MLproject                # parameters from pipeline.yaml arguments
│       └── conda.yml                # (required, not generated by this agent; typically created by user, recommended: create_env_agent)
│
└── src/                             # project-specific steps
    └── <step_name>/
        ├── run.py                   # argparse from pipeline.yaml arguments
        ├── MLproject                # parameters from pipeline.yaml arguments
        └── conda.yml                # (required, not generated by this agent; typically created by user, recommended: create_env_agent)
```

> **Note:** `conda.yml` is required for MLflow Projects but is **not generated by this agent**. It should be created by the user, and it is recommended to use `create_env_agent` for deterministic environment files.

### Shared utilities (`shared/helpers.py`, `shared/mlflow_utils.py`)

- Generated `run.py` files import parser utilities from `shared.helpers` instead of duplicating helper code in each step/component.
- Generated `main.py` and `run.py` files use `shared.mlflow_utils.configure_project_mlflow(PROJECT_ROOT)` so the root orchestrator and child step/component runs share the same MLflow tracking setup.
- The templates automatically bootstrap project-root import resolution so `shared.helpers` and `shared.mlflow_utils` work when steps/components are launched via `mlflow.run(...)`.
- Add any additional reusable/common functions in `shared/helpers.py`, `shared/mlflow_utils.py`, or nearby modules under `shared/` when multiple steps/components should share the same logic.

### `clean --keep` examples

Use `--keep` to preserve one or more step/component folders during cleaning while removing the rest of the generated project:

```bash
# Keep two steps
mlflow-pipeline-template clean ./my_project --keep download split

# Keep a step and a component
mlflow-pipeline-template clean ./my_project --keep download test_model

# Keep multiple names in one command
mlflow-pipeline-template clean ./my_project --keep download split test_model
```

Notes:
- You can pass any number of step/component names after `--keep`.
- Kept folders remain in place, and the generated orchestrator files stay so the preserved parts remain runnable.

---

## Adding steps/components later

1. Add the new step/component definition to `pipeline.yaml`
2. Re-run: `mlflow-pipeline-template generate ./my_project --config ./my_project/config.yaml --pipeline ./my_project/pipeline.yaml`
3. Implement logic in the new `run.py`

**What happens on re-run:**
- New steps/components → folders and files are generated
- Existing steps (where `run.py` already exists) → **skipped**, your code is never overwritten
- Root files (`main.py`, `MLproject`) → **regenerated** to include the new steps

---

## File ownership summary

| File | Who creates it            | Who edits it                                           |
|---|---------------------------|--------------------------------------------------------|
| `config.yaml` | User (before generation)  | User (rarely, after project setup)                     |
| `pipeline.yaml` | User (before generation)  | User (when adding steps/changing interfaces)           |
| `run.py` | Agent (generated)         | User (implements business logic)                       |
| `MLproject` | Agent (generated)         | User (adds custom parameters)                          |
| `conda.yml` | User (`create_env_agent`) | Once user completes functional code using Recommended:`create_env_agent` |
| `main.py` | Agent (generated)         | User (wire step execution order)                       |
| `shared/helpers.py` | Agent (generated)         | User (extend parser/shared utilities if needed)        |
| `shared/mlflow_utils.py` | Agent (generated)         | User (adjust shared MLflow tracking behavior if needed) |
| `AGENTS.md` | Agent (generated)         | Never — source of truth for all agents                 |


---

## Disclaimer: Step/Component Isolation and Interdependencies

This project **assumes no interdependencies between steps, components, or any other modules outside their local directories**. Each step and component is generated as an isolated unit, and the agent does not attempt to resolve or manage cross-directory imports.

If your project requires steps or components to import code from other steps, components, or shared modules outside their own directory, **you must manually configure the `PYTHONPATH` in your MLproject files** (or in your environment) so that MLflow can resolve such dependencies at runtime. The structure and management of such interdependencies is **completely left to the user** and is not handled by this tool.

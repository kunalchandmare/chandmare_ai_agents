# mlflow-pipeline-template

Generates a fully structured MLflow + Hydra pipeline project from two user-provided YAML files.

---

## Installation

```bash
pip install -e /path/to/packages/mlflow_pipeline_template
```

---

## How it works

1. Run: `mlflow-pipeline-template generate <project_path>` — creates sample `config.yaml.sample` and `pipeline.yaml.sample` in the project folder
2. User edits both files for their project
3. Run: `mlflow-pipeline-template generate <project_path> --config <path> --pipeline <path>` — generates the full ML pipeline (Path to .yaml or .yml)

**Init mode (no --config/--pipeline):** creates sample YAML files for user to edit  
**Generate mode (with --config and --pipeline):** generates the full project structure

---

## Usage

```bash
# 1. Init mode: generate sample config and pipeline files
mlflow-pipeline-template generate ./my_project

# 2. Edit config.yaml and pipeline.yaml in ./my_project

# 3. Generate mode: build full pipeline from edited files (must have .yaml extension)
mlflow-pipeline-template generate ./my_project --config ./my_project/config.yaml --pipeline ./my_project/pipeline.yaml

# 4. Implement your logic in each run.py
# 5. Run the pipeline
cd my_project
mlflow run . -P steps=all
```

## `config.yaml` — Parameter Reference

Project-level infrastructure configuration.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `project_name` | str | **yes** | — | Project name. Used as MLflow project name and folder name. |
| `project_slug` | str | no | auto from `project_name` | Python-safe slug. Auto-derived as lowercase with underscores. Override if needed. |
| `artifact_backend` | str | no | `"mlflow"` | Artifact versioning backend. One of: `mlflow`, `dvc`, `wandb`. |
| `mlflow_version` | str | no | `"2.14.1"` | MLflow version pinned in the project. |
| `wandb_entity` | str | only if `wandb` | — | W&B entity (username or team). Required when `artifact_backend: wandb`. |
| `wandb_project` | str | only if `wandb` | same as `project_name` | W&B project name. Required when `artifact_backend: wandb`. |
| `wandb_version` | str | only if `wandb` | `"0.17.0"` | W&B SDK version. |
| `dvc_remote` | str | only if `dvc` | `""` | DVC remote URL (e.g. `s3://bucket/path`). Leave empty to configure later. |

### `artifact_backend` choices

| Value | What it does |
|---|---|
| `mlflow` | Uses MLflow's built-in artifact tracking. Zero extra setup. Default. |
| `dvc` | Adds DVC for git-like data versioning. Best for large datasets (>100MB). |
| `wandb` | Uses Weights & Biases for artifact tracking. Requires account. |

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

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `type` | str | **yes** | — | Python type: `str`, `int`, `float`, `bool` |
| `default` | any | no | — | Default value. If omitted, argument has no default. |
| `required` | bool | no | `false` | If `true`, argument must be provided at runtime (no default). |
| `description` | str | no | `""` | Help text for argparse and documentation. |

### How arguments propagate

Arguments defined in `pipeline.yaml` automatically generate:

| Generated file | What's produced |
|---|---|
| `run.py` | `argparse.add_argument("--<arg_name>", type=<type>, ...)` |
| `MLproject` | `parameters: <arg_name>: { type, default, description }` |
| `config.yaml` (in generated project) | Section per step with argument keys for runtime values |

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

## Generated project structure

```text
<project_name>/
├── AGENTS.md                        ← rules for AI agents in this project
├── main.py                          ← Hydra pipeline orchestrator
├── MLproject                        ← root MLflow entry point
├── config.yaml                      ← runtime values for step arguments
├── pipeline.yaml                    ← pipeline definition (copied from input)
├── conda.yml                        ← generated by create_env_agent
│
├── components/                      ← reusable blocks
│   ├── shared/
│   │   ├── pyproject.toml
│   │   └── artifact_utils/
│   │       ├── __init__.py
│   │       ├── mlflow_artifacts.py
│   │       ├── dvc_artifacts.py     ← only if artifact_backend=dvc
│   │       ├── wandb_artifacts.py   ← only if artifact_backend=wandb
│   │       └── file_utils.py
│   └── <component_name>/
│       ├── run.py                   ← argparse from pipeline.yaml arguments
│       ├── MLproject                ← parameters from pipeline.yaml arguments
│       └── conda.yml               ← generated by create_env_agent
│
└── src/                             ← project-specific steps
    └── <step_name>/
        ├── run.py                   ← argparse from pipeline.yaml arguments
        ├── MLproject                ← parameters from pipeline.yaml arguments
        └── conda.yml               ← generated by create_env_agent
```

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

| File | Who creates it | Who edits it |
|---|---|---|
| `config.yaml` | User (before generation) | User (rarely, after project setup) |
| `pipeline.yaml` | User (before generation) | User (when adding steps/changing interfaces) |
| `run.py` | Agent (generated) | User (implements business logic) |
| `MLproject` | Agent (generated) | User (adds custom parameters) |
| `conda.yml` | `create_env_agent` | Never manually — always regenerated |
| `main.py` | Agent (generated) | User (wire step execution order) |
| `AGENTS.md` | Agent (generated) | Never — source of truth for all agents |

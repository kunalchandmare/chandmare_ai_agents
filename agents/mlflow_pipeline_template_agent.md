# mlflow_pipeline_template_agent specification

**Author:** Chandmare, Kunal  
**Model:** Claude Opus 4  
**Created:** 2026-05-06

`mlflow_pipeline_template_agent` generates a fully structured MLflow + Hydra pipeline project skeleton from two user-provided YAML files: `config.yaml` (project settings) and `pipeline.yaml` (step/component definitions with arguments).

## Command

```bash
# Init mode: creates config.yaml.sample and pipeline.yaml.sample in project folder
mlflow-pipeline-template generate <project_path>

# Generate mode: generates full pipeline (files must have .yaml extension)
mlflow-pipeline-template generate <project_path> --config <path> --pipeline <path>

# Clean mode: removes all generated artifacts, preserves user files
mlflow-pipeline-template clean <project_path>
```

### Behavior

- **Only `project_path` given (no `--config`/`--pipeline`)** → creates project folder with `config.yaml.sample` and `pipeline.yaml.sample` for user to rename and edit. Does NOT generate the pipeline.
- **`--config` and `--pipeline` given** → validates `.yaml`/`.yml` extension, parses both files, and generates the full MLflow pipeline structure in `project_path`.
- **`clean <project_path>`** → removes all generated files (`main.py`, `MLproject`, `params.yaml`) and directories (`src/`, `components/`). Preserves `config.yaml`, `pipeline.yaml`, and `*.sample` files.

## Options

- `<project_path>`: Project directory that contains `config.yaml` and `pipeline.yaml` (required)
- `--config <path>`: Path to project config YAML (must have `.yaml` or `.yml` extension)
- `--pipeline <path>`: Path to pipeline definition YAML (must have `.yaml` or `.yml` extension)

## Scope

`mlflow_pipeline_template_agent` is a pip-installable CLI tool (`pip install chandmare-mlflow-pipeline-template`).

It does not:
- implement business logic inside generated `run.py` files
- generate `conda.yml` or environment files (delegates to `create_env_agent`)
- push generated projects to remote repositories
- create conda environments

All generation happens locally from the two input YAML files.

## Guarantees

- Uses `folder_structure_agent.md` for maintaining folder structure of the agents generated artefacts; agent_name = `folder_structure`
- **Package must include `pyproject.toml`** at `packages/mlflow_pipeline_template/`. The `pyproject.toml` is the single source of truth for package metadata, build configuration, entry points, and package discovery.
- **Package author must match the agent author** (`Chandmare, Kunal`).
- User provides exactly two files: `config.yaml` and `pipeline.yaml`.
- Arguments defined in `pipeline.yaml` auto-propagate to `run.py` (argparse) and `MLproject` (parameters section). No manual duplication.
- Steps (`pipeline.yaml` → `steps:`) generate under `src/<step_name>/`.
- Components (`pipeline.yaml` → `components:`) generate under `components/<component_name>/`.
- Artifact backend choice (`mlflow`, `dvc`, `wandb`) in `config.yaml` controls what imports and boilerplate appear in each generated `run.py`:
  - `mlflow` → uses `mlflow.log_artifact()` and `mlflow.artifacts.download_artifacts()`
  - `dvc` → uses `subprocess` calls to `dvc add`, `dvc push`, `dvc pull`
  - `wandb` → uses `wandb.init()`, `wandb.Artifact`, Windows-safe download
- To ensure consistency, always generate all templates and code files directly from the parsed structure of pipeline.yaml and config.yaml, so that any change in the schema of these YAML files is automatically and accurately reflected in every generated artifact
- No separate utility library is generated — backend code lives inline in each `run.py`.
- `create_env_agent` is invoked as the final post-generation task (if installed) to produce all `conda.yml` files.
- Existing `run.py` files are never overwritten on re-run — safe to add steps incrementally.
- Generated project is clean: no `.jinja` templates, no generator scripts, no blueprint directories are copied into the output. Only runnable project files are emitted.

## Architecture rules

### `src/` — Project-Specific Steps

- Defined under `steps:` in `pipeline.yaml`
- Contain domain logic (column names, thresholds, model architecture)
- Unique to corresponding project — not reusable without modification
- Examples: `clean`, `train`, `feature_eng`, `evaluate`

### `components/` — Reusable, Schema-Agnostic Blocks

- Defined under `components:` in `pipeline.yaml`
- Generic — work with any data without modification
- Must NOT contain domain logic (column names, business rules)

### Rule of thumb

> If the function needs to understand *what's inside* the data → `steps:`  
> If the function works the same regardless of what it's processing → `components:`

## Validation rules

### config.yaml

- File must have `.yaml` or `.yml` extension
- `project_name` must be a non-empty string
- `artifact_backend` must be one of: `mlflow`, `dvc`, `wandb`
- If `artifact_backend: wandb`, `wandb_entity` must be non-empty
- If `artifact_backend: dvc`, `dvc_remote` must be a non-empty string (e.g. `s3://bucket/path`, `/local/path`)

### pipeline.yaml

- File must have `.yaml` or `.yml` extension
- Must contain at least one key under `steps:` or `components:`
- Each step/component must have a `description` string
- Each argument must have `type` (any valid Python type, e.g. `str`, `int`, `float`, `bool`, `list`, `dict`) and `description`
- If `required: true`, no `default` is needed
- If `required` is absent or false, `default` must be provided
- Empty `arguments:` is allowed (step with no parameters)

## Rules for Cleaning Projects

- When running the clean operation, if any custom (non-generated) files are detected inside generated folders (such as src/ or components/), the agent MUST:
    - Prompt the user with a warning listing the custom files.
    - Advise the user to stash these files before proceeding.
    - Provide the following git commands as guidance:
      - `git add <custom_files>`
      - `git stash push -m 'Stash custom files before cleaning'`
    - Ask for confirmation before deleting any files. If the user does not confirm, abort the clean operation.

## Output rules

Given a `pipeline.yaml` with steps `clean`, `train` and components `download_data`, `test_model`, the generated project looks like:

```text
my_ml_project/
├── config.yaml                  ← user-provided (parsed during generation)
├── pipeline.yaml                ← user-provided (read by main.py at runtime)
├── params.yaml                  ← generated: default argument values per step/component (Hydra config)
├── main.py                      ← generated: Hydra orchestrator
├── MLproject                    ← generated: root MLflow entry point
├── conda.yml                    ← generated by create_env_agent
├── shared/                      ← generated: empty utility package for user's shared code
│   └── __init__.py
│
├── src/
│   ├── clean/
│   │   ├── run.py               ← generated: argparse + backend boilerplate
│   │   ├── MLproject            ← generated: parameters from pipeline.yaml
│   │   └── conda.yml            ← generated by create_env_agent
│   └── train/
│       ├── run.py
│       ├── MLproject
│       └── conda.yml
│
└── components/
    ├── download_data/
    │   ├── run.py
    │   ├── MLproject
    │   └── conda.yml
    └── test_model/
        ├── run.py
        ├── MLproject
        └── conda.yml
```

Rules:
- `config.yaml` is parsed to drive generation decisions — NOT removed or modified
- `pipeline.yaml` stays in the project folder — `main.py` reads it at runtime for step ordering
- `params.yaml` is generated with default argument values for each step/component — `main.py` (Hydra) reads this at runtime and passes values to `mlflow.run()` parameters
- `params.yaml` `main:` section contains all `config.yaml` parameters (project_name, artifact_backend, etc.) plus `steps` and `experiment_name`
- Generated `run.py` includes backend-specific imports and boilerplate based on `artifact_backend` from `config.yaml`
- `shared/` is created at the project root as an empty Python package — user can put common utilities here
- Per-step/component `run.py` and `MLproject` are auto-generated from `pipeline.yaml` arguments
- Does NOT generate any `conda.yml` files — `create_env_agent` must be used by user as final step for each step or component to produce environment files

## Versioning

- The package is installable and versioned starting from `1.0.0`
- Template improvements are released through normal package version updates

## Repository layout

```text
chandmare_ai_agents/
  agents/
    mlflow_pipeline_template_agent.md
  packages/
    mlflow_pipeline_template/
      pyproject.toml
      README.md
      config.yaml.sample
      pipeline.yaml.sample
      src/
        mlflow_pipeline_template/
          __init__.py
          cli.py
          generator.py
          template/
            main.py.jinja
            MLproject.jinja
            _blueprints/
              step/
                run.py.jinja
                MLproject.jinja
              component/
                run.py.jinja
                MLproject.jinja
  docs/
    generated/
      mlflow_pipeline_template/
        README.md
```

## Design principles

- Install with pip, run immediately — no cloning or setup
- `config.yaml` defines *what project this is*; `pipeline.yaml` defines *what the pipeline does*
- Just provide two YAML files → get a full runnable project
- Define arguments once in `pipeline.yaml` — they appear everywhere automatically
- Pick your artifact backend at project creation time — generated code matches your choice
- This agent spec is the single source of truth for all rules
- Environment files are never handwritten — `create_env_agent` generates them
- Nothing is pushed or modified remotely

## Agent Rules

- Always place all import statements at the very top of every `.py` file, before any other code, docstrings, or comments. Imports must not appear inside functions or classes.
- Each argument (including multiplicity sets and sub-arguments) must always have a `description` field.
- When running the clean operation, if any custom (non-generated) files are detected inside generated folders, prompt the user, advise to stash, and require confirmation before deletion.
- Existing `run.py` files are never overwritten on re-run.
- Arguments defined in `pipeline.yaml` auto-propagate to all generated files (`run.py`, `MLproject`, `params.yaml`).

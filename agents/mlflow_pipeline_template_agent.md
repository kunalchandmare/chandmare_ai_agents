# mlflow_pipeline_template_agent specification

**Author:** Chandmare, Kunal  
**Model:** Claude Opus 4  
**Created:** 2026-05-06

`mlflow_pipeline_template_agent` generates a fully structured MLflow + Hydra pipeline project skeleton from two user-provided YAML files: `config.yaml` (project settings) and `pipeline.yaml` (step/component definitions with arguments).

## Command

```bash
mlflow-pipeline-template generate <output_path>
mlflow-pipeline-template generate <output_path> --config <config.yaml> --pipeline <pipeline.yaml>
```

## Options

- `<output_path>`: Destination directory for the generated project (required)
- `--config <path>`: Path to project config YAML (default: `./config.yaml`)
- `--pipeline <path>`: Path to pipeline definition YAML (default: `./pipeline.yaml`)

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
- Artifact backend is pluggable: `mlflow` (default), `dvc`, `wandb`. Backend-specific files are only included for the chosen backend.
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
- `components/shared/artifact_utils/` is the single source of truth for artifact helpers — never duplicated per step

### Rule of thumb

> If the function needs to understand *what's inside* the data → `steps:`  
> If the function works the same regardless of what it's processing → `components:`

## Validation rules

### config.yaml

- `project_name` must be a non-empty string
- `artifact_backend` must be one of: `mlflow`, `dvc`, `wandb`
- If `artifact_backend: wandb`, `wandb_entity` must be non-empty
- If `artifact_backend: dvc`, `dvc_remote` must be a non-empty string (e.g. `s3://bucket/path`, `/local/path`)

### pipeline.yaml

- Must contain at least one key under `steps:` or `components:`
- Each step/component must have a `description` string
- Each argument must have `type` (any valid Python type, e.g. `str`, `int`, `float`, `bool`, `list`, `dict`) and `description`
- If `required: true`, no `default` is needed
- If `required` is absent or false, `default` must be provided
- Empty `arguments:` is allowed (step with no parameters)

## Output rules

- Generates `main.py` — Hydra orchestrator that reads `pipeline.yaml` at runtime for step ordering
- Generates `MLproject` — root MLflow entry point
- Generates `config.yaml` — Hydra runtime config with one section per step/component (values are TODO placeholders)
- Copies `pipeline.yaml` into the generated project
- Generates `components/shared/artifact_utils/` with backend-appropriate utilities
- Generates per-step `src/<name>/run.py` and `src/<name>/MLproject`
- Generates per-component `components/<name>/run.py` and `components/<name>/MLproject`
- Does NOT generate any `conda.yml` files — `create_env_agent` handles that

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
            config.yaml.jinja
            components/
              shared/
                pyproject.toml.jinja
                artifact_utils/
                  __init__.py.jinja
                  mlflow_artifacts.py
                  dvc_artifacts.py
                  file_utils.py
                  wandb_artifacts.py
            _blueprints/
              step/
                run.py.jinja
                run_dvc.py.jinja
                run_wandb.py.jinja
                MLproject.jinja
              component/
                run.py.jinja
                run_dvc.py.jinja
                run_wandb.py.jinja
                MLproject.jinja
  docs/
    generated/
      mlflow_pipeline_template/
        README.md
```

## Design principles

- Two files, full project
- Pip-installable — no template repo cloning
- Declare, don't implement
- Single source of truth for arguments (pipeline.yaml)
- Pluggable artifact backends
- Agent-friendly (this agent spec is the single source of truth for rules)
- `create_env_agent` handles all environment generation
- No automatic remote mutation

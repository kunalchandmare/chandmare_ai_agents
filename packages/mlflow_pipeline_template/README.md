# mlflow-pipeline-template

A [Copier](https://copier.readthedocs.io/) template for generating MLflow + Weights & Biases + Hydra pipeline projects.

Declare the steps and components you need — get a fully structured skeleton with shared utilities, `AGENTS.md`, and ready-to-implement `run.py` files.

---

## Prerequisites

```bash
pip install copier jinja2 pyyaml
```

---

## Generate a new project

```bash
copier copy path/to/mlflow-pipeline-template path/to/my-new-project
```

Answer the prompts:

| Prompt | Example |
|---|---|
| `project_name` | `churn_prediction` |
| `wandb_entity` | `myteam` |
| `wandb_project` | `churn_prediction` |
| `python_version` | `3.11` |
| `mlflow_version` | `2.14.1` |
| `wandb_version` | `0.17.0` |
| `pipeline_steps` | `ingest,clean,feature_eng,train,evaluate` |
| `reusable_components` | `download_data,train_val_test_split,test_model` |

Copier will:
1. Copy and render all root template files
2. Run `generate_steps.py` → creates `src/<step>/` for each step
3. Run `generate_components.py` → creates `components/<comp>/` for each component

---

## Generated project structure

```
my-new-project/
├── AGENTS.md                        ← agent rules (read this first)
├── main.py                          ← Hydra pipeline orchestrator
├── MLproject                        ← root MLflow entry point
├── config.yaml                      ← Hydra config (one section per step)
├── conda.yml                        ← root env (managed by create_env_agent)
├── generate_steps.py                ← add new steps later
├── generate_components.py           ← add new components later
│
├── components/
│   ├── shared/
│   │   ├── pyproject.toml
│   │   └── wandb_utils/
│   │       ├── __init__.py
│   │       ├── artifact_utils.py    ← safe_artifact_download, read_one_csv_to_df, empty_dir
│   │       └── log_artifact.py      ← log_artifact()
│   ├── download_data/
│   │   ├── run.py                   ← implement reusable logic
│   │   ├── MLproject
│   │   └── conda.yml
│   └── ...
│
├── src/
│   ├── ingest/
│   │   ├── run.py                   ← implement domain logic
│   │   ├── MLproject
│   │   └── conda.yml
│   └── ...
│
└── _blueprints/                     ← used by generate_steps/generate_components
    ├── step/
    └── component/
```

---

## After generation: workflow

1. **Read `AGENTS.md`** — it describes all rules and active agents
2. **Implement** `run.py` in each `src/<step>/` and `components/<comp>/`
3. **Wire** `mlflow.run()` calls and config keys in `main.py` + `config.yaml`
4. **Run `create_env_agent`** to regenerate `conda.yml` files from your imports
5. **Run the pipeline:**
   ```bash
   mlflow run . -P steps=all
   # or run specific steps:
   mlflow run . -P steps=ingest,clean
   ```

## Add a new step later

```bash
python generate_steps.py . my_new_step
# → creates src/my_new_step/ with run.py, MLproject, conda.yml skeletons
```

## Add a new component later

```bash
python generate_components.py . my_new_component
# → creates components/my_new_component/ with run.py, MLproject, conda.yml skeletons
```

---

## Update an existing project when the template changes

```bash
copier update path/to/my-existing-project
```

Copier merges template changes with your existing code using diff/conflict resolution.

---

## components/ vs src/ — quick rule

| Put it in `components/` | Put it in `src/` |
|---|---|
| Generic artifact download | Data cleaning with specific column logic |
| Train/test split | Model training with specific architecture |
| Model evaluation scoring | Feature engineering for this domain |
| Upload artifact wrapper | Business-specific validation rules |
| Schema-agnostic → reusable | Knows column names → project-specific |


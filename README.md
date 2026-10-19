# Chandmare AI Agents

**Chandmare AI Agents** is a monorepo of modular, local-first AI agents for creating reproducible Python projects, maintaining clean repository structures, and generating MLflow + Hydra ML pipelines.

The repository separates agent specifications, installable Python packages, documentation, and tests:

```text
chandmare_ai_agents/
├── agents/       # Agent specifications
├── docs/         # Human-facing and generated documentation
├── packages/     # Installable Python packages
└── tests/        # Package and feature tests
```

## 🤖 Agents

This repository currently includes three agents:

| Agent | Purpose | Main Output |
|---|---|---|
| **Create Environment Agent** | Scans Python projects and generates reproducible dependency manifests | `requirements.txt`, `conda.yaml`, `dependency_warnings.txt` |
| **Folder Structure Agent** | Maintains a clean, scalable monorepo layout | Standardized repository structure and cleanup recommendations |
| **MLflow Pipeline Template Agent** | Generates an MLflow + Hydra ML pipeline project from YAML configuration | Runnable pipeline skeleton with steps, components, and MLproject files |

### 1. Create Environment Agent

`create_env_agent` scans local Python source files using AST, identifies third-party imports, resolves installed package versions, and generates deterministic dependency manifests.

It is designed for reproducible local setup and execution. The agent keeps PyPI as the default package source, supports optional extra package indexes, and can resolve package versions from a specified local Conda environment.

**Key features**

- Recursively scans `.py` files in a local project
- Ignores Python standard-library modules and local project imports
- Maps common import names to distribution names, such as `sklearn` → `scikit-learn` and `cv2` → `opencv-python`
- Resolves exact installed versions for directly used packages
- Generates `requirements.txt`, `conda.yaml`, and `dependency_warnings.txt`
- Supports Torch CUDA/CPU wheel index detection
- Works fully locally and does not clone, commit, or push to remote repositories

**Example**

```bash
create-env scan ./my_project --env-name my_conda_env
```

**Generated files**

```text
my_project/
├── requirements.txt
├── conda.yaml
└── dependency_warnings.txt
```

📄 Specification: [`agents/create_env_agent.md`](agents/create_env_agent.md)

### 2. Folder Structure Agent

`maintain_folder_structure_agent` keeps the repository organized as it grows with new agents, Python packages, documentation, tests, and runtime data.

It enforces a clear separation between agent specifications, installable packages, shared utilities, tests, and generated documentation. It also helps identify misplaced files, propose cleanup actions, and maintain a minimal repository root.

**Key features**

- Defines the canonical `agents/`, `packages/`, `docs/`, and `tests/` layout
- Recommends a `src/` layout for installable Python packages
- Keeps runtime data inside package folders
- Places generated reports under `docs/generated/`
- Prevents temporary files, build artifacts, and generated notes from polluting the repository root
- Supports repository cleanup after project creation or restructuring

**Preferred layout**

```text
chandmare_ai_agents/
├── README.md
├── agents/
│   ├── create_env_agent.md
│   ├── maintain_folder_structure_agent.md
│   └── mlflow_pipeline_template_agent.md
├── docs/
│   └── generated/
├── packages/
│   └── <package_name>/
│       ├── pyproject.toml
│       ├── README.md
│       └── src/
└── tests/
    └── <package_name>_test/
```

📄 Specification: [`agents/folder_structure_agent.md`](agents/folder_structure_agent.md)

### 3. MLflow Pipeline Template Agent

`mlflow_pipeline_template_agent` generates a fully structured MLflow + Hydra machine-learning pipeline project from two user-provided YAML files:

- `config.yaml`: project-level settings
- `pipeline.yaml`: pipeline steps, reusable components, and arguments

The agent creates a clean, runnable project skeleton without embedding project-specific business logic. Arguments defined once in `pipeline.yaml` are automatically propagated to generated `run.py` files and `MLproject` parameter sections.

**Key features**

- Generates MLflow + Hydra pipeline projects from YAML definitions
- Creates project-specific steps under `src/`
- Creates reusable, schema-agnostic components under `components/`
- Supports MLflow, DVC, and Weights & Biases artifact backends
- Generates `main.py`, `MLproject`, and `params.yaml`
- Preserves existing `run.py` files during regeneration
- Can clean generated artifacts while preserving user configuration files
- Delegates environment-file generation to `create_env_agent`

**Commands**

```bash
# Create sample configuration files
mlflow-pipeline-template generate ./my_ml_project

# Generate the full pipeline
mlflow-pipeline-template generate ./my_ml_project \
  --config config.yaml \
  --pipeline pipeline.yaml

# Remove generated artifacts
mlflow-pipeline-template clean ./my_ml_project
```

**Generated project structure**

```text
my_ml_project/
├── config.yaml
├── pipeline.yaml
├── params.yaml
├── main.py
├── MLproject
├── conda.yml
├── src/
│   ├── shared/
│   ├── clean/
│   └── train/
└── components/
    ├── download_data/
    └── test_model/
```

📄 Specification: [`agents/mlflow_pipeline_template_agent.md`](agents/mlflow_pipeline_template_agent.md)

## 🔗 Agent Workflow

The agents are designed to work together:

```text
MLflow Pipeline Template Agent
            │
            ├── generates pipeline project
            │
            └── invokes Create Environment Agent
                        │
                        └── generates dependency/environment files

Folder Structure Agent
            │
            └── maintains repository layout and cleanup rules
```

Typical workflow:

1. Use the **MLflow Pipeline Template Agent** to create a new ML pipeline project.
2. Use the **Create Environment Agent** to scan the generated project and produce dependency files.
3. Use the **Folder Structure Agent** to keep the monorepo organized as more agents and packages are added.

## 📦 Installation

Each agent is intended to be packaged as an installable Python tool under `packages/`.

```bash
pip install chandmare-mlflow-pipeline-template
```

For local development:

```bash
git clone https://github.com/kunalchandmare/chandmare_ai_agents.git
cd chandmare_ai_agents

python -m venv .venv
source .venv/bin/activate

pip install -e packages/<package_name>
```

## 🧪 Testing

Tests are organized by package or feature:

```bash
pytest tests/
```

Example test layout:

```text
tests/
├── create_env_test/
└── mlflow_test/
```

## 🤝 Contributing

When adding a new agent or package:

1. Add the agent specification to `agents/<agent_name>_agent.md`
2. Add the implementation under `packages/<package_name>/src/<package_name>/`
3. Add tests under `tests/<package_name>_test/`
4. Place generated documentation under `docs/generated/<agent_or_package_name>/`
5. Keep the repository root clean

## 📄 License

This project is licensed under the Apache License 2.0.

You are free to use, modify, distribute, and use this software commercially, subject to the license terms. See [LICENSE](LICENSE) for the full license text.
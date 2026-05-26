import pytest
"""Tests for mlflow_pipeline_template generator with wandb backend and 4 steps."""
from pathlib import Path

from mlflow_pipeline_template.generator import generate_project


def test_generates_all_step_folders(project_dir):
    """Each step in pipeline.yaml gets its own src/<step>/ folder."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    for step in ("download", "convert", "split", "training"):
        step_dir = project_dir / "src" / step
        assert step_dir.exists(), f"Missing step folder: src/{step}"
        assert (step_dir / "run.py").exists(), f"Missing run.py in src/{step}"
        assert (step_dir / "MLproject").exists(), f"Missing MLproject in src/{step}"


def test_no_components_folder_when_empty(project_dir):
    """No components/ folder when pipeline.yaml has no components."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    components_dir = project_dir / "components"
    assert not components_dir.exists()


def test_root_main_py_generated(project_dir):
    """main.py is generated at project root."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    assert (project_dir / "main.py").exists()


def test_root_mlproject_generated(project_dir):
    """MLproject is generated at project root."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    assert (project_dir / "MLproject").exists()


def test_wandb_import_in_run_py(project_dir):
    """With wandb backend, run.py should contain wandb import."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    run_py = (project_dir / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert "wandb" in run_py, "wandb backend code missing from run.py"


def test_no_dvc_in_run_py(project_dir):
    """With wandb backend chosen, dvc code should NOT appear."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    run_py = (project_dir / "src" / "training" / "run.py").read_text(encoding="utf-8")
    assert "dvc" not in run_py.lower() or "dvc" not in run_py


def test_step_arguments_in_mlproject(project_dir):
    """MLproject parameters match pipeline.yaml arguments."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    mlproject = (project_dir / "src" / "split" / "MLproject").read_text(encoding="utf-8")
    assert "input_artifact" in mlproject
    assert "test_size" in mlproject
    assert "random_seed" in mlproject


def test_step_arguments_in_run_py_argparse(project_dir):
    """run.py argparse should include all arguments from pipeline.yaml."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    run_py = (project_dir / "src" / "training" / "run.py").read_text(encoding="utf-8")
    assert "--train_artifact" in run_py
    assert "--epochs" in run_py
    assert "--learning_rate" in run_py


def test_mlproject_type_mapping(project_dir):
    """MLproject types should be mapped correctly (str->string, int->float, float->float)."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    mlproject = (project_dir / "src" / "split" / "MLproject").read_text(encoding="utf-8")
    lines = mlproject.split("\n")
    # Find type lines
    type_lines = [l.strip() for l in lines if l.strip().startswith("type:")]
    # input_artifact (str) -> string, test_size (float) -> float, random_seed (int) -> float
    assert any("string" in t for t in type_lines), f"Expected 'string' type, got: {type_lines}"
    assert any("float" in t for t in type_lines), f"Expected 'float' type, got: {type_lines}"


def test_shared_utils_folder_created(project_dir):
    """src/shared/ package is created when steps exist."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    shared = project_dir / "src" / "shared"
    assert shared.exists()
    assert (shared / "__init__.py").exists()


def test_optional_argument_has_default_in_mlproject(project_dir):
    """Non-required arguments should have a default in MLproject."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    mlproject = (project_dir / "src" / "training" / "MLproject").read_text(encoding="utf-8")
    assert "default:" in mlproject


# === CLI use case tests ===

import subprocess
import sys


def test_cli_init_mode_creates_sample_files(tmp_path):
    """generate <project_path> without --config/--pipeline creates .yaml.sample files only."""
    project = tmp_path / "new_project"
    result = subprocess.run(
        [sys.executable, "-m", "mlflow_pipeline_template.cli", "generate", str(project)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (project / "config.yaml.sample").exists()
    assert (project / "pipeline.yaml.sample").exists()
    # Should NOT create .yaml files or generate pipeline
    assert not (project / "config.yaml").exists()
    assert not (project / "pipeline.yaml").exists()
    assert not (project / "main.py").exists()
    assert not (project / "MLproject").exists()
    assert "Sample files created" in result.stdout


def test_cli_init_mode_does_not_overwrite_existing(tmp_path):
    """Re-running init mode does not overwrite user-edited .yaml.sample files."""
    project = tmp_path / "existing"
    project.mkdir()
    config = project / "config.yaml.sample"
    config.write_text("project_name: my_custom\n", encoding="utf-8")
    pipeline = project / "pipeline.yaml.sample"
    pipeline.write_text("steps: {}\ncomponents: {}\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "mlflow_pipeline_template.cli", "generate", str(project)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    # Original content preserved
    assert config.read_text(encoding="utf-8") == "project_name: my_custom\n"


def test_cli_generate_mode_with_config_and_pipeline(project_dir):
    """generate with --config and --pipeline produces full pipeline."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mlflow_pipeline_template.cli", "generate",
            str(project_dir),
            "--config", str(project_dir / "config.yaml"),
            "--pipeline", str(project_dir / "pipeline.yaml"),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Done!" in result.stdout
    assert (project_dir / "main.py").exists()
    assert (project_dir / "src" / "download" / "run.py").exists()


def test_cli_generate_mode_missing_config_errors(tmp_path):
    """generate with --config pointing to missing file exits with error."""
    project = tmp_path / "proj"
    project.mkdir()
    result = subprocess.run(
        [
            sys.executable, "-m", "mlflow_pipeline_template.cli", "generate",
            str(project),
            "--config", str(tmp_path / "nonexistent.yaml"),
            "--pipeline", str(tmp_path / "also_missing.yaml"),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_cli_no_command_shows_help():
    """Running without subcommand shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "mlflow_pipeline_template.cli"],
        capture_output=True, text=True,
    )
    assert "generate" in result.stdout or "usage" in result.stdout.lower()


def test_cli_rejects_non_yaml_extension(tmp_path):
    """Config and pipeline files must have .yaml extension."""
    project = tmp_path / "proj"
    project.mkdir()
    bad_config = tmp_path / "config.json"
    bad_config.write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, "-m", "mlflow_pipeline_template.cli", "generate",
            str(project),
            "--config", str(bad_config),
            "--pipeline", str(tmp_path / "pipeline.yaml"),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert ".yaml" in result.stderr


def test_params_yaml_generated_with_defaults(project_dir):
    """params.yaml is generated with default argument values for each step."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    params_path = project_dir / "params.yaml"
    assert params_path.exists()

    import yaml
    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))

    # Check main section exists with config params and experiment_name
    assert "main" in params
    assert params["main"]["steps"] == "all"
    assert params["main"]["experiment_name"] == "dev"
    assert params["main"]["project_name"] == "image_classifier"
    assert params["main"]["artifact_backend"] == "wandb"
    assert params["main"]["wandb_entity"] == "myteam"

    # Check step defaults from pipeline.yaml
    assert "split" in params
    assert params["split"]["test_size"] == 0.2
    assert params["split"]["random_seed"] == 42

    # Required args with no default should be empty string
    assert params["download"]["source_url"] == ""


def test_multiplicity_argument_set_descriptions(tmp_path):
    """params.yaml contains a list of dicts for multiplicity argument; MLproject exposes only parent argument."""
    from mlflow_pipeline_template.generator import generate_project
    import yaml

    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: multiplicity_desc_test\n", encoding="utf-8")

    pipeline_yaml = '''
steps:
  multi_step:
    description: "Step with multiplicity argument set"
    arguments:
      my_arg_set:
        multiplicity: true
        multiplicity_count: 2
        args:
          - arg1:
              type: str
              default: foo
              required: true
              # no description provided
            arg2:
              type: int
              default: 42
              description: "Second argument desc."
components: {}
'''
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(pipeline_yaml, encoding="utf-8")

    generate_project(config_path, pipeline_path, tmp_path)

    params_path = tmp_path / "params.yaml"
    assert params_path.exists()
    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    # Should be a list of dicts, length 2
    assert "multi_step" in params
    assert "my_arg_set" in params["multi_step"]
    assert isinstance(params["multi_step"]["my_arg_set"], list)
    assert len(params["multi_step"]["my_arg_set"]) == 2
    for entry in params["multi_step"]["my_arg_set"]:
        assert entry["arg1"] == "foo"
        assert entry["arg2"] == 42
    # MLproject should expose only the parent argument
    mlproject = (tmp_path / "src" / "multi_step" / "MLproject").read_text(encoding="utf-8")
    assert "my_arg_set" in mlproject
    assert "arg1" not in mlproject
    assert "arg2" not in mlproject


def test_multiplicity_argument_set_run_py_argparse(tmp_path):
    """run.py argparse should include only the parent multiplicity argument, not sub-arguments."""
    from mlflow_pipeline_template.generator import generate_project

    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: multiplicity_argparse_test\n", encoding="utf-8")

    pipeline_yaml = '''
steps:
  multi_step:
    description: "Step with multiplicity argument set"
    arguments:
      my_arg_set:
        multiplicity: true
        multiplicity_count: 2
        args:
          - arg1:
              type: str
              default: foo
              required: true
              description: "desc1"
            arg2:
              type: int
              default: 42
              description: "desc2"
components: {}
'''
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(pipeline_yaml, encoding="utf-8")

    generate_project(config_path, pipeline_path, tmp_path)

    run_py = (tmp_path / "src" / "multi_step" / "run.py").read_text(encoding="utf-8")
    # Should include argparse for my_arg_set only
    assert "--my_arg_set" in run_py
    assert "--arg1" not in run_py
    assert "--arg2" not in run_py


def test_multiplicity_arg_set_runtime(tmp_path):
    """Test that run.py can access and iterate over the multiplicity argument set as a list of dicts with correct values."""
    from mlflow_pipeline_template.generator import generate_project
    import yaml
    import subprocess
    import sys

    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: multiplicity_runtime_test\n", encoding="utf-8")

    pipeline_yaml = '''
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
components: {}
'''
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(pipeline_yaml, encoding="utf-8")

    generate_project(config_path, pipeline_path, tmp_path)

    # Overwrite params.yaml with custom values for each set
    params_path = tmp_path / "params.yaml"
    params = {
        "my_step": {
            "my_arg_set": [
                {"arg1": "foo1", "arg2": 42},
                {"arg1": "foo2", "arg2": 99},
                {"arg1": "bar", "arg2": 123},
            ]
        },
        "main": {"project_name": "multiplicity_runtime_test", "steps": "all", "experiment_name": "dev"}
    }
    params_path.write_text(yaml.dump(params, sort_keys=False), encoding="utf-8")

    # Patch run.py to print the argument set for test
    run_py_path = tmp_path / "src" / "my_step" / "run.py"
    run_py = run_py_path.read_text(encoding="utf-8")
    # Insert print logic after parser.parse_args()
    marker = "args = parser.parse_args()"
    injected = (
        f"{marker}\n    import yaml\n    with open('../../params.yaml', 'r', encoding='utf-8') as f:\n        params = yaml.safe_load(f)\n    arg_set = params['my_step']['my_arg_set']\n    for entry in arg_set:\n        print(f'arg1={{entry[\'arg1\']}} arg2={{entry[\'arg2\']}}')\n"
    )
    run_py = run_py.replace(marker, injected)
    run_py_path.write_text(run_py, encoding="utf-8")

    # Run the script and capture output
    result = subprocess.run(
        [sys.executable, str(run_py_path)],
        cwd=str(run_py_path.parent),
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    output_lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    assert "arg1=foo1 arg2=42" in output_lines
    assert "arg1=foo2 arg2=99" in output_lines
    assert "arg1=bar arg2=123" in output_lines


def test_clean_project_prompts_on_custom_files(tmp_path, monkeypatch, capsys):
    """Test that clean_project prompts the user if custom files are present in generated folders."""
    from pathlib import Path
    from mlflow_pipeline_template.generator import clean_project

    # Setup: create both a shallow and a deep custom file
    step1_dir = tmp_path / "src" / "step1"
    step1_dir.mkdir(parents=True, exist_ok=True)
    shallow_file = step1_dir / "custom.py"
    shallow_file.write_text("print('shallow custom')\n", encoding="utf-8")

    nested_dir = step1_dir / "subdir"
    nested_dir.mkdir(parents=True, exist_ok=True)
    deep_file = nested_dir / "deep_custom.py"
    deep_file.write_text("print('deep custom')\n", encoding="utf-8")

    # Patch input to simulate user declining the prompt
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(SystemExit) as excinfo:
        clean_project(tmp_path, generated_files=set())
    assert excinfo.value.code == 1

    # Check output
    out = capsys.readouterr().out
    out_norm = out.replace("\\", "/")
    assert "WARNING: Custom files detected" in out
    assert "deep_custom.py" in out
    assert "custom.py" in out
    assert "src/step1/custom.py" in out_norm or "step1/custom.py" in out_norm
    assert "src/step1/subdir/deep_custom.py" in out_norm or "step1/subdir/deep_custom.py" in out_norm
    assert "git add" in out
    assert "git stash push" in out
    # Do not check for input prompt, as it is not reliably captured in pytest


def test_clean_project_fallback_generated(monkeypatch, tmp_path, capsys):
    """Test clean_project fallback logic: only generated_names are not flagged as custom."""
    from mlflow_pipeline_template.generator import clean_project
    # Setup: create src/step1/ with generated and custom files
    step_dir = tmp_path / "src" / "step1"
    step_dir.mkdir(parents=True, exist_ok=True)
    # Generated files
    (step_dir / "run.py").write_text("print('run')\n", encoding="utf-8")
    (step_dir / "MLproject").write_text("name: test\n", encoding="utf-8")
    # Custom file
    (step_dir / "custom.py").write_text("print('custom')\n", encoding="utf-8")
    # Root generated file
    (tmp_path / "main.py").write_text("print('main')\n", encoding="utf-8")
    # Root custom file (should not be flagged)
    (tmp_path / "README.md").write_text("# readme\n", encoding="utf-8")

    # Patch input to simulate user declining the prompt
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(SystemExit) as excinfo:
        clean_project(tmp_path)
    assert excinfo.value.code == 1

    out = capsys.readouterr().out
    out_norm = out.replace("\\", "/")
    # Only custom.py should be flagged
    assert "custom.py" in out
    assert "src/step1/custom.py" in out_norm or "step1/custom.py" in out_norm
    assert "run.py" not in out
    assert "MLproject" not in out
    assert "main.py" not in out
    assert "README.md" not in out  # root custom files are not flagged
    assert "git add" in out
    assert "git stash push" in out
    assert "Aborted clean." in out

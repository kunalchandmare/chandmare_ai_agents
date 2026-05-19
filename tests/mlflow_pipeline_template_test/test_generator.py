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

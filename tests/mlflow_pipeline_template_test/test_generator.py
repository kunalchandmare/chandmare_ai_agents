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


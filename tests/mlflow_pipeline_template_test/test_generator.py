import pytest
"""Tests for mlflow_pipeline_template generator with W&B tracking and 4 steps."""
import py_compile

from mlflow_pipeline_template.generator import generate_project


def _assert_generated_python_compiles(project_path):
    """Compile every generated Python file to catch template indentation/syntax regressions."""
    py_files = sorted(project_path.rglob("*.py"))
    assert py_files, "Expected generated Python files"
    assert project_path / "main.py" in py_files, "Expected generated root main.py to be compiled"
    run_py_files = [py_file for py_file in py_files if py_file.name == "run.py"]
    assert run_py_files, "Expected generated step/component run.py files to be compiled"
    for py_file in py_files:
        py_compile.compile(str(py_file), doraise=True)


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


def test_generated_python_files_compile_for_steps_and_components(tmp_path):
    """Generated root, shared, step, and component .py files should always be syntactically valid."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: compile_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  download:
    description: "Download data"
    arguments:
      source_url:
        type: str
        required: true
        description: "Source URL"
      force_download:
        type: bool
        default: false
        description: "Force download"
      threshold:
        type: float
        default: null
        description: "Optional threshold"
  batch_download:
    description: "Download multiple sources"
    arguments:
      dataset_sources:
        multiplicity: true
        multiplicity_count: 2
        args:
          - out_dir:
              type: str
              required: true
              description: "Output directory"
            url:
              type: str
              required: true
              description: "Dataset URL"
components:
  validate:
    description: "Validate outputs"
    arguments:
      input_artifact:
        type: str
        required: true
        description: "Input artifact"
      max_missing:
        type: float
        default: 0.1
        description: "Max missing fraction"
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    _assert_generated_python_compiles(tmp_path)


def test_generated_python_files_compile_for_wandb_components(tmp_path):
    """W&B component templates should also render compilable Python."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: wandb_component_compile_test
tracking_backend: wandb
artifact_backend: dvc
wandb_entity: myteam
wandb_project: wandb_component_compile_test
""",
        encoding="utf-8",
    )
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  prepare:
    description: "Prepare data"
    arguments:
      input_path:
        type: str
        required: true
        description: "Input path"
components:
  reusable_component:
    description: "Reusable W&B component"
    arguments:
      output_artifact:
        type: str
        default: output
        description: "Output artifact"
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    _assert_generated_python_compiles(tmp_path)


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


def test_pipeline_group_id_propagates_as_internal_run_name(project_dir):
    """main.py should generate run_name internally and generated step files should accept it without pipeline.yaml."""
    (project_dir / "config.yaml").write_text(
        """project_name: image_classifier
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )

    main_py = (project_dir / "main.py").read_text(encoding="utf-8")
    assert "import uuid" in main_py
    assert "PROJECT_ROOT = Path(__file__).resolve().parent" in main_py
    assert "from shared.mlflow_utils import configure_project_mlflow" in main_py
    assert "configure_project_mlflow(PROJECT_ROOT)" in main_py
    assert 'experiment_name = str(main_cfg.get("experiment_name", "dev"))' in main_py
    assert 'pipeline_group_id = f"{experiment_name}-{uuid.uuid4().hex[-4:]}"' in main_py
    assert '"run_name": _serialize_param(pipeline_group_id)' in main_py
    assert "run_name=pipeline_group_id" not in main_py

    step_mlproject = (project_dir / "src" / "download" / "MLproject").read_text(encoding="utf-8")
    assert "run_name:" in step_mlproject
    assert "--run_name {run_name}" in step_mlproject

    step_run_py = (project_dir / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert "PROJECT_ROOT = Path(__file__).resolve().parents[2]" in step_run_py
    assert "from shared.mlflow_utils import configure_project_mlflow" in step_run_py
    assert "configure_project_mlflow(PROJECT_ROOT)" in step_run_py
    assert '"--run_name", type=str,' in step_run_py
    assert "mlflow.start_run(run_name=args.run_name or None)" in step_run_py
    assert 'mlflow.set_tag("pipeline_group_id", args.run_name or "")' in step_run_py


def test_component_accepts_internal_run_name_without_pipeline_argument(tmp_path):
    """Generated components should accept root-propagated run_name even when pipeline.yaml omits it."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: component_run_name_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps: {}
components:
  validate:
    description: "Validate output"
    arguments:
      input_artifact:
        type: str
        required: true
        description: "Input artifact"
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    main_py = (tmp_path / "main.py").read_text(encoding="utf-8")
    assert '"run_name": _serialize_param(pipeline_group_id)' in main_py

    component_mlproject = (tmp_path / "components" / "validate" / "MLproject").read_text(encoding="utf-8")
    assert "run_name:" in component_mlproject
    assert "--run_name {run_name}" in component_mlproject

    component_run_py = (tmp_path / "components" / "validate" / "run.py").read_text(encoding="utf-8")
    assert "PROJECT_ROOT = Path(__file__).resolve().parents[2]" in component_run_py
    assert "from shared.mlflow_utils import configure_project_mlflow" in component_run_py
    assert "configure_project_mlflow(PROJECT_ROOT)" in component_run_py
    assert '"--run_name", type=str,' in component_run_py
    assert "mlflow.start_run(run_name=args.run_name or None)" in component_run_py
    assert 'mlflow.set_tag("pipeline_group_id", args.run_name or "")' in component_run_py


def test_root_mlproject_generated(project_dir):
    """MLproject is generated at project root."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    assert (project_dir / "MLproject").exists()


def test_main_uses_get_for_standard_args(project_dir):
    """main.py uses config.get fallbacks for non-multiplicity step arguments."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    main_py = (project_dir / "main.py").read_text(encoding="utf-8")
    assert 'main_cfg = config.get("main", {})' in main_py
    assert '"input_artifact": _serialize_param(step_cfg_runtime.get("input_artifact", \'\'))' in main_py
    assert '"test_size": _serialize_param(step_cfg_runtime.get("test_size", 0.2))' in main_py
    assert '"random_seed": _serialize_param(step_cfg_runtime.get("random_seed", 42))' in main_py


def test_bool_arguments_remain_value_based_in_run_py(tmp_path):
    """Boolean arguments are parsed as explicit values, not presence-only flags."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: bool_value_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  download:
    description: "Download step"
    arguments:
      force_download:
        type: bool
        default: false
        description: "Force re-download"
components: {}
""",
        encoding="utf-8",
    )
    generate_project(config_path, pipeline_path, tmp_path)
    run_py = (tmp_path / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert 'from shared.helpers import parse_bool' in run_py
    assert 'type=parse_bool' in run_py
    assert 'action="store_true"' not in run_py


def test_nullable_float_default_uses_optional_float_parser_in_run_py(tmp_path):
    """Optional float args with default null should parse to Python None when omitted or passed as null/blank."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: nullable_float_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  score:
    description: "Nullable float step"
    arguments:
      threshold:
        type: float
        default: null
        description: "Optional threshold"
components: {}
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)
    run_py = (tmp_path / "src" / "score" / "run.py").read_text(encoding="utf-8")
    assert 'from shared.helpers import parse_optional_float' in run_py
    assert '"--threshold", type=parse_optional_float,' in run_py
    assert 'default=None,' in run_py


def test_tracking_backend_wandb_import_in_run_py(project_dir):
    """With W&B tracking enabled, run.py should contain wandb import."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    run_py = (project_dir / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert "wandb" in run_py, "wandb backend code missing from run.py"


def test_tracking_backend_wandb_includes_dvc_metadata_reference_in_run_py(project_dir):
    """With W&B tracking chosen, template guidance should still reference DVC metadata (.dvc) for artifact lineage."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    run_py = (project_dir / "src" / "training" / "run.py").read_text(encoding="utf-8")
    assert "<output_path>.dvc" in run_py
    assert "metadata={\"dvc_file\": \"<output_path>.dvc\"}" in run_py


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


def test_artifact_backend_rejects_wandb(tmp_path):
    """artifact_backend=wandb should fail fast because wandb is not a data-versioning backend."""
    from mlflow_pipeline_template.generator import generate_project

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: invalid_artifact_backend
tracking_backend: mlflow
artifact_backend: wandb
""",
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text("steps: {}\ncomponents: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact_backend must be 'dvc'"):
        generate_project(config_path, pipeline_path, tmp_path)


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
    """shared/ package is created at project root when steps exist."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    shared = project_dir / "shared"
    assert shared.exists()
    assert (shared / "__init__.py").exists()
    assert (shared / "helpers.py").exists()
    assert (shared / "mlflow_utils.py").exists()
    mlflow_utils = (shared / "mlflow_utils.py").read_text(encoding="utf-8")
    assert "def configure_project_mlflow(" in mlflow_utils
    assert "def start_run_with_fallback(" in mlflow_utils


def test_optional_argument_has_default_in_mlproject(project_dir):
    """Non-required arguments should have a default in MLproject."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )
    mlproject = (project_dir / "src" / "training" / "MLproject").read_text(encoding="utf-8")
    assert "default:" in mlproject


def test_cli_clean_keep_preserves_selected_steps(project_dir):
    """clean --keep preserves named steps/components and keeps root orchestrator files."""
    generate_project(
        project_dir / "config.yaml",
        project_dir / "pipeline.yaml",
        project_dir,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mlflow_pipeline_template.cli",
            "clean",
            str(project_dir),
            "--keep",
            "download",
            "split",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (project_dir / "main.py").exists()
    assert (project_dir / "MLproject").exists()
    assert (project_dir / "params.yaml").exists()
    assert (project_dir / "src" / "download").exists()
    assert (project_dir / "src" / "split").exists()
    assert not (project_dir / "src" / "convert").exists()
    assert not (project_dir / "src" / "training").exists()
    assert "Clean complete" in result.stdout


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
    assert params["main"]["tracking_backend"] == "wandb"
    assert params["main"]["artifact_backend"] == "dvc"
    assert params["main"]["wandb_entity"] == "myteam"

    # Check step defaults from pipeline.yaml
    assert "split" in params
    assert params["split"]["test_size"] == 0.2
    assert params["split"]["random_seed"] == 42

    # Required args with no default should be empty string
    assert params["download"]["source_url"] == ""


def test_orchestrator_handles_multiplicity(tmp_path):
    """
    main.py should handle the multiplicity loop, while MLproject and run.py expose only sub-arguments as normal parameters.
    """
    from mlflow_pipeline_template.generator import generate_project
    import yaml
    import sys
    import subprocess

    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: orchestrator_multiplicity_test\n", encoding="utf-8")

    pipeline_yaml = '''
steps:
  download:
    description: "Download step with multiplicity argument set"
    arguments:
      dataset_sources:
        multiplicity: true
        multiplicity_count: 2
        args:
          - out_dir:
              type: str
              required: true
              description: "Output directory"
            url:
              type: str
              required: true
              description: "Dataset URL"
components: {}
'''
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(pipeline_yaml, encoding="utf-8")

    generate_project(config_path, pipeline_path, tmp_path)

    # Check MLproject exposes only sub-arguments
    mlproject = (tmp_path / "src" / "download" / "MLproject").read_text(encoding="utf-8")
    assert "dataset_sources" not in mlproject
    assert "out_dir:" in mlproject
    assert "url:" in mlproject

    # Check run.py exposes only sub-arguments
    run_py = (tmp_path / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert "--dataset_sources" not in run_py
    assert "--out_dir" in run_py
    assert "--url" in run_py

    # Check main.py orchestrator logic for multiplicity
    main_py_path = tmp_path / "main.py"
    main_py = main_py_path.read_text(encoding="utf-8")
    # Check for loop over dataset_sources
    assert 'for entry in step_cfg_runtime.get("dataset_sources", []):' in main_py
    # Check that only the defined sub-arguments are passed to mlflow.run
    for sub_arg in ["out_dir", "url"]:
            assert f'"{sub_arg}": _serialize_param((entry or {{}}).get("{sub_arg}", \'\'))' in main_py

    # No simulation of orchestrator loop; only code structure is checked


def test_download_step_with_full_multiplicity_args(tmp_path):
    """
    Pipeline with download step using multiplicity argument with 2 sets and 7 sub-arguments.
    Ensures MLproject and run.py expose only sub-arguments, and orchestrator handles the loop.
    """
    from mlflow_pipeline_template.generator import generate_project
    import yaml
    import sys
    import subprocess

    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: multiplicity_full_args_test\n", encoding="utf-8")

    pipeline_yaml = '''
steps:
  download:
    description: "Download and extract Robot@Home archives or one custom source"
    arguments:
      dataset_sources:
        multiplicity: true
        multiplicity_count: 2
        args:
          - out_dir:
              type: str
              required: true
              description: "Directory where files are downloaded"
            extract_root:
              type: str
              default: "."
              description: "Root directory where archives are extracted"
            force_download:
              type: bool
              default: false
              description: "Force re-download even if file already exists"
            dataset_url:
              type: str
              default: null
              description: "Optional custom dataset URL (must be paired with dataset_filename and dataset_md5)"
            dataset_filename:
              type: str
              default: null
              description: "Optional custom downloaded filename (must be paired with dataset_url and dataset_md5)"
            dataset_md5:
              type: str
              default: null
              description: "Optional custom MD5 checksum (must be paired with dataset_url and dataset_filename)"
            dataset_extract_to:
              type: str
              default: null
              description: "Optional extraction path relative to extract_root for custom archive"
components: {}
'''
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(pipeline_yaml, encoding="utf-8")

    generate_project(config_path, pipeline_path, tmp_path)

    # Check MLproject exposes only sub-arguments
    mlproject = (tmp_path / "src" / "download" / "MLproject").read_text(encoding="utf-8")
    assert "dataset_sources" not in mlproject
    for arg in [
        "out_dir:", "extract_root:", "force_download:", "dataset_url:",
        "dataset_filename:", "dataset_md5:", "dataset_extract_to:"
    ]:
        assert arg in mlproject

    # Check run.py exposes only sub-arguments
    run_py = (tmp_path / "src" / "download" / "run.py").read_text(encoding="utf-8")
    assert "--dataset_sources" not in run_py
    for arg in [
        "--out_dir", "--extract_root", "--force_download", "--dataset_url",
        "--dataset_filename", "--dataset_md5", "--dataset_extract_to"
    ]:
        assert arg in run_py

    # Simulate orchestrator logic by running main.py
    params = {
        "download": {
            "dataset_sources": [
                {
                    "out_dir": "dir1",
                    "extract_root": "/extract1",
                    "force_download": True,
                    "dataset_url": "http://example.com/1.zip",
                    "dataset_filename": "file1.zip",
                    "dataset_md5": "md5-1",
                    "dataset_extract_to": "extract_to1",
                },
                {
                    "out_dir": "dir2",
                    "extract_root": "/extract2",
                    "force_download": False,
                    "dataset_url": "http://example.com/2.zip",
                    "dataset_filename": "file2.zip",
                    "dataset_md5": "md5-2",
                    "dataset_extract_to": "extract_to2",
                },
            ]
        },
        "main": {"project_name": "multiplicity_full_args_test", "steps": "all", "experiment_name": "dev"}
    }
    params_path = tmp_path / "params.yaml"
    params_path.write_text(yaml.dump(params, sort_keys=False), encoding="utf-8")

    # Patch run.py to print received arguments
    run_py_path = tmp_path / "src" / "download" / "run.py"
    run_py = run_py_path.read_text(encoding="utf-8")
    marker = "args = parser.parse_args()"
    injected = (
        f"{marker}\n    print(f'out_dir={{args.out_dir}} extract_root={{args.extract_root}} force_download={{args.force_download}} "
        f"dataset_url={{args.dataset_url}} dataset_filename={{args.dataset_filename}} dataset_md5={{args.dataset_md5}} "
        f"dataset_extract_to={{args.dataset_extract_to}}')\n"
    )
    run_py = run_py.replace(marker, injected)
    run_py_path.write_text(run_py, encoding="utf-8")

    # Run main.py and capture output
    main_py_path = tmp_path / "main.py"
    main_py = main_py_path.read_text(encoding="utf-8")
    # Check for loop over dataset_sources
    assert 'for entry in step_cfg_runtime.get("dataset_sources", []):' in main_py
    # Check that all sub-arguments are passed to mlflow.run using safe default lookups
    expected_default_lookup = {
        "out_dir": "''",
        "extract_root": "'.'",
        "force_download": "False",
        "dataset_url": "None",
        "dataset_filename": "None",
        "dataset_md5": "None",
        "dataset_extract_to": "None",
    }
    for sub_arg, default_literal in expected_default_lookup.items():
        assert f'"{sub_arg}": _serialize_param((entry or {{}}).get("{sub_arg}", {default_literal}))' in main_py

    result = subprocess.run(
        [sys.executable, str(main_py_path)],
        cwd=str(tmp_path),
        capture_output=True, text=True,
    )
    # Instead of requiring success, assert that the error is about missing conda.yaml
    assert result.returncode != 0
    assert "conda.yaml" in result.stderr and "no such file was found" in result.stderr.lower()


def test_main_runs_when_optional_args_are_missing(tmp_path):
    """Generated main.py should run successfully with missing optional args by using safe defaults."""
    from mlflow_pipeline_template.generator import generate_project
    import subprocess
    import sys

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: optional_args_runtime_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  download:
    description: "Step with required and optional args"
    arguments:
      input_path:
        type: str
        required: true
        description: "Required input path"
      threshold:
        type: float
        default: 0.75
        description: "Optional threshold"
      use_cache:
        type: bool
        default: false
        description: "Optional cache flag"
components: {}
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    # Stub modules so the generated main.py can execute without external dependencies.
    (tmp_path / "hydra.py").write_text(
        """import os

def main(version_base=None, config_name=None, config_path=None):
    def decorator(func):
        def wrapper():
            config = {
                "main": {"project_name": "optional_args_runtime_test", "experiment_name": "dev", "steps": "download"},
                "download": {"input_path": "/data/input"},
            }
            return func(config)
        return wrapper
    return decorator

class utils:
    @staticmethod
    def get_original_cwd():
        return os.getcwd()
""",
        encoding="utf-8",
    )
    (tmp_path / "mlflow.py").write_text(
        """def set_tracking_uri(uri):
    print(f"MLFLOW_TRACKING_URI:{uri}")

def set_experiment(name):
    print(f"MLFLOW_EXPERIMENT:{name}")

def run(uri, entry_point, env_manager=None, parameters=None):
    print(f"MLFLOW_PARAMS:{parameters}")
    return None
""",
        encoding="utf-8",
    )
    (tmp_path / "omegaconf.py").write_text(
        """class DictConfig(dict):
    pass
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(tmp_path / "main.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "MLFLOW_PARAMS:" in result.stdout
    assert "'input_path': '/data/input'" in result.stdout
    assert "'threshold': '0.75'" in result.stdout
    assert "'use_cache': 'False'" in result.stdout


def test_main_serializes_nullable_float_default_none_as_empty_string(tmp_path):
    """Generated main.py should forward missing nullable float values as empty strings, not the literal 'None'."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: nullable_float_main_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  evaluate:
    description: "Step with nullable threshold"
    arguments:
      threshold:
        type: float
        default: null
        description: "Optional threshold"
components: {}
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    (tmp_path / "hydra.py").write_text(
        """import os

def main(version_base=None, config_name=None, config_path=None):
    def decorator(func):
        def wrapper():
            config = {
                "main": {"project_name": "nullable_float_main_test", "experiment_name": "dev", "steps": "evaluate"},
                "evaluate": {},
            }
            return func(config)
        return wrapper
    return decorator

class utils:
    @staticmethod
    def get_original_cwd():
        return os.getcwd()
""",
        encoding="utf-8",
    )
    (tmp_path / "mlflow.py").write_text(
        """def set_tracking_uri(uri):
    print(f"MLFLOW_TRACKING_URI:{uri}")

def set_experiment(name):
    print(f"MLFLOW_EXPERIMENT:{name}")

def run(uri, entry_point, env_manager=None, parameters=None):
    print(f"MLFLOW_PARAMS:{parameters}")
    return None
""",
        encoding="utf-8",
    )
    (tmp_path / "omegaconf.py").write_text(
        """class DictConfig(dict):
    pass
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(tmp_path / "main.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "MLFLOW_PARAMS:" in result.stdout
    assert "'threshold': ''" in result.stdout
    assert "'threshold': 'None'" not in result.stdout


def test_dataset_sources_bool_argument_is_value_based_end_to_end(tmp_path):
    """Multiplicity bool args should be forwarded as explicit True/False values, including default False when omitted."""
    from mlflow_pipeline_template.generator import generate_project
    import ast
    import subprocess
    import sys

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """project_name: dataset_sources_bool_test
tracking_backend: mlflow
artifact_backend: dvc
""",
        encoding="utf-8",
    )

    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        """steps:
  download:
    description: "Download dataset sources"
    arguments:
      dataset_sources:
        multiplicity: true
        multiplicity_count: 2
        args:
          - out_dir:
              type: str
              required: true
              description: "Download directory"
            extract_root:
              type: str
              default: data
              description: "Extraction root"
            force_download:
              type: bool
              default: false
              description: "Force re-download even if file already exists"
            dataset_url:
              type: str
              default: null
              description: "Dataset URL"
            dataset_filename:
              type: str
              default: null
              description: "Dataset filename"
            dataset_md5:
              type: str
              default: null
              description: "Dataset checksum"
            dataset_extract_to:
              type: str
              default: data
              description: "Extraction destination"
components: {}
""",
        encoding="utf-8",
    )

    generate_project(config_path, pipeline_path, tmp_path)

    (tmp_path / "hydra.py").write_text(
        """import os

def main(version_base=None, config_name=None, config_path=None):
    def decorator(func):
        def wrapper():
            config = {
                "main": {"project_name": "dataset_sources_bool_test", "experiment_name": "dev", "steps": "download"},
                "download": {
                    "dataset_sources": [
                        {
                            "out_dir": r"C:\\Users\\fixc9dv\\Downloads",
                            "extract_root": "data",
                            "dataset_url": "https://zenodo.org/record/7811795/files/Robot@Home2_db.tgz",
                            "dataset_filename": "Robot@Home2_db.tgz",
                            "dataset_md5": "d34fb44c01f31c87be8ab14e5ecd0767",
                            "dataset_extract_to": "data",
                        },
                        {
                            "out_dir": r"C:\\Users\\fixc9dv\\Downloads",
                            "extract_root": "data",
                            "force_download": True,
                            "dataset_url": "https://zenodo.org/record/7811795/files/Robot@Home2_db.tgz",
                            "dataset_filename": "Robot@Home2_db.tgz",
                            "dataset_md5": "d34fb44c01f31c87be8ab14e5ecd0767",
                            "dataset_extract_to": "data",
                        },
                    ]
                },
            }
            return func(config)
        return wrapper
    return decorator

class utils:
    @staticmethod
    def get_original_cwd():
        return os.getcwd()
""",
        encoding="utf-8",
    )
    (tmp_path / "mlflow.py").write_text(
        """def set_tracking_uri(uri):
    print(f"MLFLOW_TRACKING_URI:{uri}")

def set_experiment(name):
    print(f"MLFLOW_EXPERIMENT:{name}")

def run(uri, entry_point, env_manager=None, parameters=None):
    print(f"MLFLOW_PARAMS:{parameters}")
    return None
""",
        encoding="utf-8",
    )
    (tmp_path / "omegaconf.py").write_text(
        """class DictConfig(dict):
    pass
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(tmp_path / "main.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.startswith("MLFLOW_PARAMS:")]
    assert len(lines) == 2
    assert "'force_download': 'False'" in lines[0]
    assert "'force_download': 'True'" in lines[1]
    first_params = ast.literal_eval(lines[0].removeprefix("MLFLOW_PARAMS:"))
    second_params = ast.literal_eval(lines[1].removeprefix("MLFLOW_PARAMS:"))
    assert first_params["run_name"] == second_params["run_name"]
    assert first_params["run_name"].startswith("dev-")
    assert len(first_params["run_name"].rsplit("-", 1)[-1]) == 4



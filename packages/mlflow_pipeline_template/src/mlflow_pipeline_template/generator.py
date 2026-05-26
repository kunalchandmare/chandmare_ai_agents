import shutil
import os
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader

"""
Core generator — reads config.yaml + pipeline.yaml and produces the full project.
"""
# Template and blueprint directories are shipped with the package
_PACKAGE_DIR = Path(__file__).parent
_TEMPLATE_DIR = _PACKAGE_DIR / "template"
_BLUEPRINTS_DIR = _PACKAGE_DIR / "template" / "_blueprints"


def generate_project(config_path: Path, pipeline_path: Path, output_path: Path) -> None:
    """Generate a full MLflow pipeline project."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    pipeline = yaml.safe_load(pipeline_path.read_text(encoding="utf-8")) or {}

    # Derive slug
    project_name = config.get("project_name", "my_project")
    config.setdefault("project_slug", project_name.lower().replace(" ", "_"))

    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Render root template files (main.py, MLproject)
    _render_root_templates(config, pipeline, output_path)

    # 2. Generate params.yaml with default argument values for each step/component
    _generate_params_yaml(pipeline, output_path, config)

    # 2. Generate src/<step>/ folders from pipeline.yaml steps
    steps = pipeline.get("steps", {})
    if steps:
        # Create src/shared/ as an empty utility package for user's shared step code
        shared_dir = output_path / "src" / "shared"
        shared_dir.mkdir(parents=True, exist_ok=True)
        init_file = shared_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Shared utilities for pipeline steps."""\n', encoding="utf-8")

    for step_name, step_config in steps.items():
        _generate_step_or_component(
            step_name, step_config or {}, config,
            blueprint_type="step",
            output_dir=output_path / "src" / step_name,
        )

    # 3. Generate components/<comp>/ folders from pipeline.yaml components
    components = pipeline.get("components", {})
    for comp_name, comp_config in components.items():
        _generate_step_or_component(
            comp_name, comp_config or {}, config,
            blueprint_type="component",
            output_dir=output_path / "components" / comp_name,
        )


    backend = config.get("artifact_backend", "mlflow")
    print(f"Generated {len(steps)} steps and {len(components)} components (artifact_backend: {backend})")
    if steps:
        print(f"  Steps: {', '.join(steps.keys())}")
    if components:
        print(f"  Components: {', '.join(components.keys())}")


def _render_root_templates(config: dict, pipeline: dict, output_path: Path) -> None:
    """Render Jinja templates from template/ into the output root."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )

    steps = pipeline.get("steps", {})
    components = pipeline.get("components", {})
    ctx = {
        **config,
        "steps": steps,
        "components": components,
        "step_names": list(steps.keys()),
        "component_names": list(components.keys()),
    }

    for tmpl_file in _TEMPLATE_DIR.iterdir():
        if tmpl_file.is_file() and tmpl_file.suffix == ".jinja":
            out_name = tmpl_file.stem  # strip .jinja
            rendered = env.get_template(tmpl_file.name).render(ctx)
            (output_path / out_name).write_text(rendered, encoding="utf-8")


def _generate_step_or_component(
    name: str, step_config: dict, config: dict,
    blueprint_type: str, output_dir: Path
) -> None:
    """Generate a single step or component folder from blueprints."""
    blueprint_dir = _BLUEPRINTS_DIR / blueprint_type
    if not blueprint_dir.exists():
        return

    # Do not overwrite existing run.py (safe incremental addition)
    if (output_dir / "run.py").exists():
        print(f"  SKIP {blueprint_type}/{name} — run.py already exists")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(blueprint_dir)),
        keep_trailing_newline=True,
    )

    # Preprocess arguments for multiplicity and ensure 'description' exists
    arguments = step_config.get("arguments", {})
    processed_arguments = {}
    for arg_name, arg_cfg in arguments.items():
        if isinstance(arg_cfg, dict) and arg_cfg.get("multiplicity", False):
            # Ensure each sub-argument in 'args' has a description
            args_list = []
            for sub_arg in arg_cfg.get("args", []):
                fixed_sub_arg = {}
                for sub_name, sub_cfg in sub_arg.items():
                    fixed_sub_cfg = dict(sub_cfg)
                    if "description" not in fixed_sub_cfg:
                        fixed_sub_cfg["description"] = ""
                    fixed_sub_arg[sub_name] = fixed_sub_cfg
                args_list.append(fixed_sub_arg)
            processed_arguments[arg_name] = {
                "multiplicity": True,
                "multiplicity_count": arg_cfg.get("multiplicity_count", 1),
                "args": args_list
            }
        else:
            fixed_cfg = dict(arg_cfg)
            if "description" not in fixed_cfg:
                fixed_cfg["description"] = ""
            processed_arguments[arg_name] = fixed_cfg
    ctx = {
        **config,
        "step_name": name,
        "description": step_config.get("description", ""),
        "arguments": processed_arguments,
    }

    for tmpl_path in sorted(blueprint_dir.iterdir()):
        if tmpl_path.suffix != ".jinja":
            continue

        out_name = tmpl_path.stem  # strip .jinja
        rendered = env.get_template(tmpl_path.name).render(ctx)
        (output_dir / out_name).write_text(rendered, encoding="utf-8")


def _generate_params_yaml(pipeline: dict, output_path: Path, config: dict) -> None:
    """Generate params.yaml with default argument values for each step and component."""
    # Main section includes all config.yaml parameters plus experiment_name
    main_params = {
        "steps": "all",
        "experiment_name": "dev",
    }
    for key, value in config.items():
        if key not in ("project_slug",):  # skip derived keys
            main_params[key] = value

    params = {"main": main_params}

    for section in ("steps", "components"):
        for name, cfg in pipeline.get(section, {}).items():
            if not cfg:
                continue
            arguments = cfg.get("arguments", {})
            if not arguments:
                params[name] = {}
                continue
            step_params = {}
            for arg_name, arg_cfg in arguments.items():
                # Multiplicity support
                if isinstance(arg_cfg, dict) and arg_cfg.get("multiplicity", False):
                    count = arg_cfg.get("multiplicity_count", 1)
                    args_list = []
                    for sub_arg in arg_cfg.get("args", []):
                        fixed_sub_arg = {}
                        for sub_name, sub_cfg in sub_arg.items():
                            fixed_sub_cfg = dict(sub_cfg)
                            if "description" not in fixed_sub_cfg:
                                fixed_sub_cfg["description"] = ""
                            fixed_sub_arg[sub_name] = fixed_sub_cfg
                        args_list.append(fixed_sub_arg)
                    # For params.yaml, store as a list of dicts with defaults
                    step_params[arg_name] = []
                    for i in range(count):
                        entry = {}
                        for sub_arg in args_list:
                            for sub_name, sub_cfg in sub_arg.items():
                                entry[sub_name] = sub_cfg.get("default", "")
                        step_params[arg_name].append(entry)
                else:
                    fixed_cfg = dict(arg_cfg)
                    if "description" not in fixed_cfg:
                        fixed_cfg["description"] = ""
                    step_params[arg_name] = fixed_cfg.get("default", "")
            params[name] = step_params

    params_path = output_path / "params.yaml"
    params_path.write_text(
        yaml.dump(params, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def clean_project(output_path: Path, generated_files: set = None):
    """Remove all generated artifacts except config.yaml and pipeline.yaml. Warn if custom files are detected."""

    # List of files/folders to preserve
    preserve = {"config.yaml", "pipeline.yaml", "config.yaml.sample", "pipeline.yaml.sample"}
    # List of generated file names to consider as generated in any folder
    generated_names = {"main.py", "MLproject", "params.yaml", "run.py"}
    # Folders to clean
    folders = ["src", "components"]

    # Fallback: if generated_files is not provided, build a set of generated files
    fallback_generated = set()
    # Add all generated-named files in root and under src/ and components/
    for folder in ["."] + folders:
        folder_path = output_path if folder == "." else output_path / folder
        if folder_path.exists():
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for fname in filenames:
                    if fname in generated_names:
                        fpath = Path(dirpath) / fname
                        rel_path = str(fpath.relative_to(output_path))
                        fallback_generated.add(rel_path)

    # Use fallback if generated_files is None
    effective_generated = generated_files if generated_files is not None else fallback_generated

    # Detect custom files in src/ and components/
    custom_files = []
    for folder in folders:
        folder_path = output_path / folder
        if folder_path.exists():
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for fname in filenames:
                    fpath = Path(dirpath) / fname
                    rel_path = str(fpath.relative_to(output_path))
                    if rel_path not in effective_generated:
                        custom_files.append(rel_path)

    if custom_files:
        print("WARNING: Custom files detected in generated folders:")
        for f in custom_files:
            print(f"  - {f}")
        print("\nBefore cleaning, you may want to stash these files:")
        print("  git add " + " ".join(custom_files))
        print("  git stash push -m 'Stash custom files before cleaning'\n")
        resp = input("Proceed with cleaning? [y/N]: ")
        if resp.strip().lower() != "y":
            print("Aborted clean.")
            raise SystemExit(1)

    # Remove generated root files
    for fname in generated_names:
        f = output_path / fname
        if f.exists():
            f.unlink()
    # Remove generated folders
    for folder in folders:
        folder_path = output_path / folder
        if folder_path.exists():
            shutil.rmtree(folder_path)
    # Remove params.yaml
    params_path = output_path / "params.yaml"
    if params_path.exists():
        params_path.unlink()
    print("Clean complete.")

if __name__ == "__main__":
  import sys
  clean_project(Path(sys.argv[1]))
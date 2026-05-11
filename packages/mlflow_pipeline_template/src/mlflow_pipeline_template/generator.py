"""
Core generator — reads config.yaml + pipeline.yaml and produces the full project.
"""
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

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

    # 1. Render root template files (main.py, MLproject, config.yaml, AGENTS.md)
    _render_root_templates(config, pipeline, output_path)

    # 2. Copy shared utility files (artifact_utils)
    _copy_shared_utils(config, output_path)

    # 3. Generate src/<step>/ folders from pipeline.yaml steps
    steps = pipeline.get("steps", {})
    for step_name, step_config in steps.items():
        _generate_step_or_component(
            step_name, step_config or {}, config,
            blueprint_type="step",
            output_dir=output_path / "src" / step_name,
        )

    # 4. Generate components/<comp>/ folders from pipeline.yaml components
    components = pipeline.get("components", {})
    for comp_name, comp_config in components.items():
        _generate_step_or_component(
            comp_name, comp_config or {}, config,
            blueprint_type="component",
            output_dir=output_path / "components" / comp_name,
        )

    # 5. Copy pipeline.yaml into generated project
    shutil.copy2(str(pipeline_path), str(output_path / "pipeline.yaml"))

    # 6. Run create_env_agent (best-effort)
    _run_create_env(output_path)

    print(f"Generated {len(steps)} steps and {len(components)} components")


def _render_root_templates(config: dict, pipeline: dict, output_path: Path) -> None:
    """Render Jinja templates from template/ into the output root."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )

    # Build context with all config + pipeline info for root templates
    steps = pipeline.get("steps", {})
    components = pipeline.get("components", {})
    ctx = {
        **config,
        "steps": steps,
        "components": components,
        "step_names": list(steps.keys()),
        "component_names": list(components.keys()),
    }

    # Render each .jinja file in template/ root (skip directories)
    for tmpl_file in _TEMPLATE_DIR.iterdir():
        if tmpl_file.is_file() and tmpl_file.suffix == ".jinja":
            out_name = tmpl_file.stem  # strip .jinja
            rendered = env.get_template(tmpl_file.name).render(ctx)
            (output_path / out_name).write_text(rendered, encoding="utf-8")


def _copy_shared_utils(config: dict, output_path: Path) -> None:
    """Copy components/shared/ into the generated project, rendering .jinja files."""
    shared_src = _TEMPLATE_DIR / "components" / "shared"
    shared_dst = output_path / "components" / "shared"
    shared_dst.mkdir(parents=True, exist_ok=True)

    backend = config.get("artifact_backend", "mlflow")

    for item in shared_src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(shared_src)
        dst_file = shared_dst / rel

        # Skip backend-specific files not in use
        if "wandb_artifacts" in item.name and backend != "wandb":
            continue
        if "dvc_artifacts" in item.name and backend != "dvc":
            continue

        dst_file.parent.mkdir(parents=True, exist_ok=True)

        if item.suffix == ".jinja":
            # Render jinja template
            env = Environment(
                loader=FileSystemLoader(str(item.parent)),
                keep_trailing_newline=True,
            )
            rendered = env.get_template(item.name).render(config)
            out_path = dst_file.with_suffix("")  # strip .jinja from output name
            out_path.write_text(rendered, encoding="utf-8")
        else:
            shutil.copy2(str(item), str(dst_file))


def _generate_step_or_component(
    name: str, step_config: dict, config: dict,
    blueprint_type: str, output_dir: Path
) -> None:
    """Generate a single step or component folder from blueprints."""
    blueprint_dir = _BLUEPRINTS_DIR / blueprint_type
    if not blueprint_dir.exists():
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(blueprint_dir)),
        keep_trailing_newline=True,
    )

    backend = config.get("artifact_backend", "mlflow")
    run_templates = {
        "mlflow": "run.py.jinja",
        "dvc": "run_dvc.py.jinja",
        "wandb": "run_wandb.py.jinja",
    }
    active_run = run_templates.get(backend, "run.py.jinja")

    ctx = {
        **config,
        "step_name": name,
        "description": step_config.get("description", ""),
        "arguments": step_config.get("arguments", {}),
    }

    for tmpl_path in sorted(blueprint_dir.iterdir()):
        if tmpl_path.suffix != ".jinja":
            continue
        # Skip run variants not in use
        if tmpl_path.name in run_templates.values() and tmpl_path.name != active_run:
            continue

        out_name = tmpl_path.stem
        if tmpl_path.name in run_templates.values():
            out_name = "run.py"

        rendered = env.get_template(tmpl_path.name).render(ctx)
        (output_dir / out_name).write_text(rendered, encoding="utf-8")


def _run_create_env(output_path: Path) -> None:
    """Best-effort: run create_env_agent to generate conda.yml files."""
    import subprocess
    try:
        subprocess.run(
            ["python", "-m", "create_env", "scan", str(output_path)],
            check=False, capture_output=True, timeout=60,
            input=b"n\n",  # auto-decline any prompts
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # create_env not installed or timed out — user can run it later


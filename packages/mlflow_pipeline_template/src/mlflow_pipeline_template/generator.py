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

    # 1. Render root template files (main.py, MLproject)
    _render_root_templates(config, pipeline, output_path)

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


    print(f"Generated {len(steps)} steps and {len(components)} components")


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

    ctx = {
        **config,
        "step_name": name,
        "description": step_config.get("description", ""),
        "arguments": step_config.get("arguments", {}),
    }

    for tmpl_path in sorted(blueprint_dir.iterdir()):
        if tmpl_path.suffix != ".jinja":
            continue

        out_name = tmpl_path.stem  # strip .jinja
        rendered = env.get_template(tmpl_path.name).render(ctx)
        (output_dir / out_name).write_text(rendered, encoding="utf-8")



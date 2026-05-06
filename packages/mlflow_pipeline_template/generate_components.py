#!/usr/bin/env python
"""
generate_components.py — called by Copier _tasks after the main template copy.

Also callable manually to add a new reusable component to an existing generated project:
    python generate_components.py . new_component
    python generate_components.py . comp_a,comp_b
"""
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import yaml


def load_context(project_root: Path) -> dict:
    answers_file = project_root / ".copier-answers.yml"
    if answers_file.exists():
        answers = yaml.safe_load(answers_file.read_text(encoding="utf-8")) or {}
    else:
        answers = {}
    return {
        "python_version": answers.get("python_version", "3.11"),
        "wandb_version": answers.get("wandb_version", "0.17.0"),
        "mlflow_version": answers.get("mlflow_version", "2.14.1"),
    }


def render_component(blueprint_dir: Path, output_dir: Path, comp_name: str, context: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(str(blueprint_dir)),
        keep_trailing_newline=True,
    )
    ctx = {**context, "step_name": comp_name}  # blueprints use step_name variable
    for tmpl_path in sorted(blueprint_dir.iterdir()):
        if tmpl_path.suffix == ".jinja":
            out_name = tmpl_path.stem
            rendered = env.get_template(tmpl_path.name).render(ctx)
            (output_dir / out_name).write_text(rendered, encoding="utf-8")
            print(f"  wrote {out_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_components.py <project_root> [comp1,comp2,...]")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    comps_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    comp_names = [c.strip() for c in comps_arg.split(",") if c.strip()]

    if not comp_names:
        print("[generate_components] No components provided, nothing to do.")
        sys.exit(0)

    blueprint_dir = project_root / "_blueprints" / "component"
    if not blueprint_dir.exists():
        print(f"[generate_components] ERROR: blueprint dir not found: {blueprint_dir}")
        sys.exit(1)

    context = load_context(project_root)

    for comp in comp_names:
        out = project_root / "components" / comp
        if out.exists():
            print(f"[generate_components] SKIP '{comp}' — components/{comp}/ already exists")
            continue
        print(f"[generate_components] Creating components/{comp}/")
        render_component(blueprint_dir, out, comp, context)
        print(f"[generate_components] Done: components/{comp}/")


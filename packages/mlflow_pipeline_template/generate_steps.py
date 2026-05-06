#!/usr/bin/env python
"""
generate_steps.py — called by Copier _tasks after the main template copy.

Also callable manually to add a new step to an existing generated project:
    python generate_steps.py . new_step_name
    python generate_steps.py . step_a,step_b,step_c
"""
import sys
import shutil
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


def render_step(blueprint_dir: Path, output_dir: Path, step_name: str, context: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(str(blueprint_dir)),
        keep_trailing_newline=True,
    )
    ctx = {**context, "step_name": step_name}
    for tmpl_path in sorted(blueprint_dir.iterdir()):
        if tmpl_path.suffix == ".jinja":
            out_name = tmpl_path.stem  # strip .jinja extension
            rendered = env.get_template(tmpl_path.name).render(ctx)
            (output_dir / out_name).write_text(rendered, encoding="utf-8")
            print(f"  wrote {out_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_steps.py <project_root> [step1,step2,...]")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    steps_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    step_names = [s.strip() for s in steps_arg.split(",") if s.strip()]

    if not step_names:
        print("[generate_steps] No steps provided, nothing to do.")
        sys.exit(0)

    blueprint_dir = project_root / "_blueprints" / "step"
    if not blueprint_dir.exists():
        print(f"[generate_steps] ERROR: blueprint dir not found: {blueprint_dir}")
        sys.exit(1)

    context = load_context(project_root)

    for step in step_names:
        out = project_root / "src" / step
        if out.exists():
            print(f"[generate_steps] SKIP '{step}' — src/{step}/ already exists")
            continue
        print(f"[generate_steps] Creating src/{step}/")
        render_step(blueprint_dir, out, step, context)
        print(f"[generate_steps] Done: src/{step}/")


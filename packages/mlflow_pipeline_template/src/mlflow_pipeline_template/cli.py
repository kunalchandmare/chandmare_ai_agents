"""
CLI entry point for mlflow-pipeline-template.

Usage:
    mlflow-pipeline-template generate <project_path>
    mlflow-pipeline-template generate <project_path> --config config.yaml --pipeline pipeline.yaml
"""
import argparse
import shutil
import sys
from pathlib import Path

from .generator import generate_project

_PACKAGE_DIR = Path(__file__).parent


def _find_sample(name: str) -> Path:
    """Locate a sample file shipped with the package."""
    # Primary: shipped inside the package directory
    candidate = _PACKAGE_DIR / name
    if candidate.exists():
        return candidate
    # Fallback: editable install, samples at package root
    candidate = _PACKAGE_DIR.parent.parent.parent / name
    if candidate.exists():
        return candidate
    return Path("")


def main():
    parser = argparse.ArgumentParser(
        prog="mlflow-pipeline-template",
        description="Generate MLflow + Hydra pipeline projects from config.yaml + pipeline.yaml",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate a new pipeline project")
    gen_parser.add_argument("project_path", help="Project directory containing config.yaml and pipeline.yaml")
    gen_parser.add_argument(
        "--config", default=None,
        help="Path to project config file (default: <project_path>/config.yaml)"
    )
    gen_parser.add_argument(
        "--pipeline", default=None,
        help="Path to pipeline definition file (default: <project_path>/pipeline.yaml)"
    )

    args = parser.parse_args()

    if args.command == "generate":
        project_path = Path(args.project_path)
        project_path.mkdir(parents=True, exist_ok=True)

        # If --config and --pipeline provided → generate full pipeline
        if args.config and args.pipeline:
            config_path = Path(args.config)
            pipeline_path = Path(args.pipeline)

            if config_path.suffix not in (".yaml", ".yml"):
                print(f"Error: config file must have .yaml extension, got: {config_path.name}", file=sys.stderr)
                sys.exit(1)
            if pipeline_path.suffix not in (".yaml", ".yml"):
                print(f"Error: pipeline file must have .yaml extension, got: {pipeline_path.name}", file=sys.stderr)
                sys.exit(1)

            if not config_path.exists():
                print(f"Error: config file not found: {config_path}", file=sys.stderr)
                sys.exit(1)
            if not pipeline_path.exists():
                print(f"Error: pipeline file not found: {pipeline_path}", file=sys.stderr)
                sys.exit(1)

            generate_project(config_path, pipeline_path, project_path)
            print(f"Done! Project generated at: {project_path}")
            return 0

        # Otherwise → init mode: copy sample files for user to edit
        config_path = project_path / "config.yaml"
        pipeline_path = project_path / "pipeline.yaml"

        if not config_path.exists():
            sample = _find_sample("config.yaml.sample")
            if sample.exists():
                shutil.copy2(sample, config_path)
                print(f"Created sample: {config_path}")
            else:
                print("Error: sample config.yaml.sample not found in package", file=sys.stderr)
                sys.exit(1)

        if not pipeline_path.exists():
            sample = _find_sample("pipeline.yaml.sample")
            if sample.exists():
                shutil.copy2(sample, pipeline_path)
                print(f"Created sample: {pipeline_path}")
            else:
                print("Error: sample pipeline.yaml.sample not found in package", file=sys.stderr)
                sys.exit(1)

        print(f"\nSample files created in: {project_path}")
        print("Edit config.yaml and pipeline.yaml, then re-run with:")
        print(f"  mlflow-pipeline-template generate {project_path} --config {config_path} --pipeline {pipeline_path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

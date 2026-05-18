"""
CLI entry point for mlflow-pipeline-template.

Usage:
    mlflow-pipeline-template generate <project_path>
    mlflow-pipeline-template generate <project_path> --config config.yaml --pipeline pipeline.yaml
"""
import argparse
import sys
from pathlib import Path

from .generator import generate_project


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
        config_path = Path(args.config) if args.config else project_path / "config.yaml"
        pipeline_path = Path(args.pipeline) if args.pipeline else project_path / "pipeline.yaml"

        if not project_path.exists():
            print(f"Error: project directory not found: {project_path}", file=sys.stderr)
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

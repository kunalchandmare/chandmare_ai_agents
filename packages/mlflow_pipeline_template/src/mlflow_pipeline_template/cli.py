"""
CLI entry point for mlflow-pipeline-template.

Usage:
    mlflow-pipeline-template generate <output_path>
    mlflow-pipeline-template generate <output_path> --config config.yaml --pipeline pipeline.yaml
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
    gen_parser.add_argument("output_path", help="Destination directory for the generated project")
    gen_parser.add_argument(
        "--config", default="config.yaml",
        help="Path to project config file (default: config.yaml in current dir)"
    )
    gen_parser.add_argument(
        "--pipeline", default="pipeline.yaml",
        help="Path to pipeline definition file (default: pipeline.yaml in current dir)"
    )

    args = parser.parse_args()

    if args.command == "generate":
        config_path = Path(args.config)
        pipeline_path = Path(args.pipeline)
        output_path = Path(args.output_path)

        if not config_path.exists():
            print(f"Error: config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        if not pipeline_path.exists():
            print(f"Error: pipeline file not found: {pipeline_path}", file=sys.stderr)
            sys.exit(1)

        generate_project(config_path, pipeline_path, output_path)
        print(f"Done! Project generated at: {output_path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())


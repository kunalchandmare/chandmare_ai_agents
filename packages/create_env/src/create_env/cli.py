"""
CLI - Command-line interface for create_env agent.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .generator import ManifestGenerator
from .scanner import DependencyScanner


class CreateEnvCLI:
    """Command-line interface for the local create_env agent."""

    def __init__(self):
        self.scanner = DependencyScanner()
        self.input_func = input

    def run(self, args: Optional[list] = None) -> int:
        """Run the CLI and return an exit code."""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        try:
            if parsed_args.command == 'scan':
                return self._handle_scan(parsed_args)

            parser.print_help()
            return 1
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            prog='create_env',
            description='Scan local Python source files and create deterministic dependency manifests'
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        scan_parser = subparsers.add_parser('scan', help='Scan Python files and generate dependency manifests')

        scan_parser.add_argument('project_path', help='Local path to scan recursively')
        scan_parser.add_argument(
            '--env-name',
            default=None,
            help='Resolve versions from a specific local conda environment'
        )
        scan_parser.add_argument(
            '--extra-index-url',
            action='append',
            default=[],
            help='Additional package index URL (can be provided multiple times; PyPI stays default index)'
        )

        return parser

    def _handle_scan(self, args) -> int:
        """Handle the local scan command."""
        project_path = Path(args.project_path)
        env_name = args.env_name
        extra_index_urls = args.extra_index_url

        print(f"Scanning local directory: {project_path}")
        resolved_imports = self.scanner.scan_directory(str(project_path))

        if self.scanner.pending_mapping_updates:
            self._handle_mapping_update_permission()

        print(f"Found {len(resolved_imports)} external dependencies")

        generator = ManifestGenerator(resolved_imports, self.scanner.warnings)

        print(f"Resolving versions from environment: {env_name or 'active'}")
        generator.resolve_versions(env_name)

        print(f"Generating manifests in: {project_path}")
        generator.generate_all_manifests(
            str(project_path),
            environment_name='create-env-generated',
            additional_index_urls=extra_index_urls,
        )

        print('Done!')
        return 0

    def _confirm_action(self, prompt: str) -> bool:
        """Ask the user for explicit permission before performing local side effects."""
        while True:
            response = self.input_func(prompt).strip().lower()
            if response in {'y', 'yes'}:
                return True
            if response in {'', 'n', 'no'}:
                return False
            print("Please answer with 'y' or 'n'.")

    def _handle_mapping_update_permission(self) -> None:
        """Ask permission before writing unresolved imports to local override mapping."""
        unresolved_imports = ', '.join(sorted(self.scanner.pending_mapping_updates.keys()))
        override_file = self.scanner.get_default_override_mapping_path()
        prompt = (
            f"Unresolved imports detected ({unresolved_imports}). Update local override mapping file "
            f"{override_file} with null placeholders? [y/N]: "
        )

        if self._confirm_action(prompt):
            updated = self.scanner.persist_pending_mapping_updates()
            if updated:
                print(f"Updated local override mapping file: {override_file}")
        else:
            self.scanner.warnings.append(
                f"User declined updating local override mapping file {override_file}."
            )


def main(args: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    cli = CreateEnvCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main())

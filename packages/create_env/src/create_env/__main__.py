"""
Main entry point for running create_env as a module.

Usage: python -m create_env scan <project_path> [options]
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())


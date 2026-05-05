"""
create_env - Dependency Scanner and Environment Generator

Scans local Python source files with AST and creates deterministic dependency manifests.
"""

__version__ = "0.0.1"
__author__ = "chandmare_ai_agents"
__description__ = "Scans local Python source files and creates deterministic dependency manifests"

from .scanner import DependencyScanner
from .generator import ManifestGenerator

__all__ = [
    "DependencyScanner",
    "ManifestGenerator",
]


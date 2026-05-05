"""
Test configuration and fixtures for create_env tests
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the package to the path for testing (src/ layout)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'packages' / 'create_env' / 'src'))


def create_test_python_project(temp_dir: str, files_config: dict) -> None:
    """
    Create a test Python project with specified files.
    
    Args:
        temp_dir: Temporary directory path
        files_config: Dictionary with file names as keys and content as values
    """
    for file_name, content in files_config.items():
        file_path = Path(temp_dir) / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(content)


def remove_test_dir(path: str) -> None:
    """
    Remove test directory recursively.
    
    Args:
        path: Path to directory to remove
    """
    if os.path.exists(path):
        shutil.rmtree(path)


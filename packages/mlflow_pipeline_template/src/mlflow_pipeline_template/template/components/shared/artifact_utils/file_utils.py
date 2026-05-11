"""
File utility helpers — backend-agnostic.
Used by all artifact backends.

Import in any step:
    from components.shared.artifact_utils.file_utils import (
        read_one_csv_to_df,
        empty_dir,
    )
"""
import shutil
from pathlib import Path


def read_one_csv_to_df(artifact_dir: Path):
    """
    Read the single CSV file from a directory into a DataFrame.

    Args:
        artifact_dir: Path to a directory containing exactly one CSV file.

    Returns:
        pandas.DataFrame

    Raises:
        RuntimeError: If there is not exactly one CSV file in the directory.
    """
    import pandas as pd

    csv_files = list(Path(artifact_dir).glob("*.csv"))
    if len(csv_files) != 1:
        raise RuntimeError(
            f"Expected exactly 1 CSV file in {artifact_dir}, found {len(csv_files)}: {csv_files}"
        )
    return pd.read_csv(csv_files[0])


def empty_dir(dir_path: Path) -> None:
    """
    Remove all contents of a directory without deleting the directory itself.
    Use at the end of each step to clean up local artifact cache.
    """
    p = Path(dir_path)
    if not p.exists():
        return
    for child in p.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


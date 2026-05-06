"""
DVC artifact helpers.
Git-like versioning for data files and model artifacts.

Import in any step:
    from components.shared.artifact_utils.dvc_artifacts import (
        track_artifact,
        push_artifact,
        pull_artifact,
    )
"""
import subprocess
from pathlib import Path


def track_artifact(local_path: str) -> Path:
    """
    Add a file or directory to DVC tracking.
    Creates a .dvc file and adds the original to .gitignore.

    Returns:
        Path to the created .dvc file.
    """
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(f"Cannot track: {local_path} does not exist")
    subprocess.run(["dvc", "add", str(path)], check=True)
    return path.with_suffix(path.suffix + ".dvc")


def push_artifact(local_path: str = None) -> None:
    """
    Push tracked artifacts to the configured DVC remote.
    If local_path is given, pushes only that .dvc file's data.
    """
    cmd = ["dvc", "push"]
    if local_path:
        dvc_file = str(Path(local_path).with_suffix(Path(local_path).suffix + ".dvc"))
        cmd.append(dvc_file)
    subprocess.run(cmd, check=True)


def pull_artifact(local_path: str = None) -> Path:
    """
    Pull artifacts from DVC remote.
    If local_path is given, pulls only that specific artifact.

    Returns:
        Path to the pulled artifact (or cwd if pulling all).
    """
    cmd = ["dvc", "pull"]
    if local_path:
        dvc_file = str(Path(local_path).with_suffix(Path(local_path).suffix + ".dvc"))
        cmd.append(dvc_file)
    subprocess.run(cmd, check=True)
    if local_path:
        return Path(local_path).resolve()
    return Path.cwd()


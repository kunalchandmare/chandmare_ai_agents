"""
MLflow-native artifact helpers.
Default backend — zero extra dependencies beyond MLflow itself.

Import in any step:
    from components.shared.artifact_utils.mlflow_artifacts import (
        log_artifact_file,
        download_artifact,
    )
"""
import mlflow
from pathlib import Path


def log_artifact_file(local_path: str, artifact_path: str = None) -> None:
    """Log a local file as an MLflow artifact in the active run."""
    mlflow.log_artifact(local_path, artifact_path)


def download_artifact(artifact_uri: str, dst_path: str = None) -> Path:
    """
    Download an MLflow artifact by URI.

    Args:
        artifact_uri: MLflow artifact URI (e.g. 'runs:/<run_id>/output.csv')
        dst_path: Optional local destination path

    Returns:
        Absolute Path to the downloaded artifact.
    """
    local = mlflow.artifacts.download_artifacts(
        artifact_uri=artifact_uri, dst_path=dst_path
    )
    return Path(local).resolve()


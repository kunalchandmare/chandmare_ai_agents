"""
Weights & Biases artifact helpers.
Windows-safe: avoids colons in local file paths.

Only included in projects generated with artifact_backend=wandb.

Import in any step:
    from components.shared.artifact_utils.wandb_artifacts import (
        safe_artifact_download,
        log_artifact,
    )
"""
import shutil
from pathlib import Path

import wandb


def safe_artifact_download(artifact: wandb.Artifact, safe_root: str = "safe_artifacts") -> Path:
    """
    Download a W&B artifact to a Windows-safe local path (no colons).

    Args:
        artifact: A wandb.Artifact instance obtained via run.use_artifact()
        safe_root: Name of the local folder used as download root

    Returns:
        Absolute Path to the downloaded artifact directory.
    """
    if not isinstance(artifact, wandb.Artifact):
        raise ValueError("artifact must be a wandb.Artifact instance")

    safe_name = artifact.name.replace(":", "_") if artifact.name else "unnamed_artifact"
    target_dir = Path.cwd() / safe_root / safe_name
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloaded = artifact.download(root=str(target_dir))
        return Path(downloaded).resolve()
    except Exception as exc:
        raise RuntimeError(f"Failed to download artifact '{artifact.name}': {exc}") from exc


def log_artifact(
    artifact_name: str,
    artifact_type: str,
    artifact_description: str,
    local_path: str,
    run: wandb.sdk.wandb_run.Run,
) -> None:
    """Create a W&B artifact from a local file and log it to the active run."""
    artifact = wandb.Artifact(
        artifact_name,
        type=artifact_type,
        description=artifact_description,
    )
    artifact.add_file(local_path)
    run.log_artifact(artifact)
    artifact.wait()


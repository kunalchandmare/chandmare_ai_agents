"""Shared fixtures for mlflow_pipeline_template tests."""
import sys
from pathlib import Path

import pytest

# Add the package to the path for testing (src/ layout)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'packages' / 'mlflow_pipeline_template' / 'src'))

CONFIG_WANDB = """\
project_name: "image_classifier"
artifact_backend: "wandb"
mlflow_version: "2.14.1"
wandb_entity: "myteam"
wandb_project: "image_classifier"
wandb_version: "0.17.0"
"""

PIPELINE_STEPS_ONLY = """\
steps:
  download:
    description: "Download raw data from remote source"
    arguments:
      source_url:
        type: str
        required: true
        description: "URL to fetch raw data"
      output_artifact:
        type: str
        required: true
        description: "Name for the output artifact"

  convert:
    description: "Convert raw data to processed format"
    arguments:
      input_artifact:
        type: str
        required: true
        description: "Artifact from download step"
      output_format:
        type: str
        default: "parquet"
        description: "Target file format"

  split:
    description: "Split data into train and test sets"
    arguments:
      input_artifact:
        type: str
        required: true
        description: "Processed data artifact"
      test_size:
        type: float
        default: 0.2
        description: "Fraction of data for test"
      random_seed:
        type: int
        default: 42
        description: "Random seed for reproducibility"

  training:
    description: "Train the model"
    arguments:
      train_artifact:
        type: str
        required: true
        description: "Training data artifact"
      epochs:
        type: int
        default: 10
        description: "Number of training epochs"
      learning_rate:
        type: float
        default: 0.001
        description: "Learning rate"

components: {}
"""


@pytest.fixture
def project_dir(tmp_path):
    """Create a temp project directory with config.yaml and pipeline.yaml."""
    config_file = tmp_path / "config.yaml"
    pipeline_file = tmp_path / "pipeline.yaml"
    config_file.write_text(CONFIG_WANDB, encoding="utf-8")
    pipeline_file.write_text(PIPELINE_STEPS_ONLY, encoding="utf-8")
    return tmp_path


"""Compatibility paths for the canonical pipeline. New code uses explicit configuration."""
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
ML_DIR = PROJECT_DIR / "ml"
DATASET_DIR = PROJECT_DIR / "backend/DataSet"
MANIFEST_PATH = ML_DIR / "data/manifest.json"
SAVED_MODELS_DIR = ML_DIR / "saved_models"
IMAGE_MODEL_PATH = SAVED_MODELS_DIR / "approved.pt"
OUTPUTS_DIR = ML_DIR / "outputs"

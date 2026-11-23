"""Inference only from explicitly configured, strict ResNet18 checkpoints."""
import os
import threading
import time
from pathlib import Path

import torch
from PIL import Image, ImageOps

from ml.checkpoints import load_checkpoint, file_sha256
from ml.gradcam import gradcam

ROOT = Path(__file__).resolve().parents[2]
_lock = threading.Lock()


class ImagePredictor:
    def __init__(self, checkpoint=None):
        self.path = Path(checkpoint or os.environ.get("MODEL_CHECKPOINT", ROOT / "ml/saved_models/approved.pt"))

    def predict(self, image_path, heatmap_path):
        with _lock:
            torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "4")))
            model, metadata, transform = load_checkpoint(self.path)
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
            start = time.perf_counter()
            overlay, probabilities = gradcam(model, transform(image).unsqueeze(0), image)
            overlay.save(heatmap_path, format="PNG")
            index = max(range(len(probabilities)), key=lambda i: probabilities[i])
            return {"predicted_class": metadata["classes"][index],
                    "probabilities": dict(zip(metadata["classes"], probabilities)),
                    "architecture": "ResNet18", "model_version": metadata["version"],
                    "model_sha256": file_sha256(self.path), "model_metadata": metadata,
                    "inference_ms": (time.perf_counter() - start) * 1000,
                    "notice": "Research decision support, not a confirmed medical diagnosis."}


def get_predictor():
    return ImagePredictor()

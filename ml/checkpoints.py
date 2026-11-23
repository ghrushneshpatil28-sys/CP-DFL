"""Strict, self-describing ResNet18 checkpoint contract. No inferred class order."""
import hashlib
from pathlib import Path

import torch
from torchvision import transforms
from torchvision.transforms import InterpolationMode

from ml.models import build_resnet18
from ml.models.resnet18 import use_group_norm

DEFAULT_PREPROCESS = {"image_size": 224, "mean": [.485, .456, .406],
                      "std": [.229, .224, .225], "resize": "square", "interpolation": "bilinear", "color_mode": "RGB"}


def preprocessing(config):
    if config.get("resize") != "square" or config.get("interpolation") != "bilinear" or config.get("color_mode") != "RGB":
        raise ValueError("Unsupported preprocessing contract")
    size = config["image_size"]
    if not isinstance(size, int) or not 32 <= size <= 1024:
        raise ValueError("Invalid input size")
    if len(config["mean"]) != 3 or len(config["std"]) != 3 or min(config["std"]) <= 0:
        raise ValueError("Invalid normalization")
    return transforms.Compose([transforms.Resize((size, size), interpolation=InterpolationMode.BILINEAR),
                               transforms.ToTensor(), transforms.Normalize(config["mean"], config["std"])])


def save_checkpoint(path, model, metadata):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"schema_version": 1, "state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, "metadata": metadata}, path)


def load_checkpoint(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Approved ResNet18 checkpoint missing; train and approve a model first")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("schema_version") != 1 or "metadata" not in payload:
        raise ValueError("Legacy checkpoint lacks verified class/preprocessing metadata; retraining required")
    meta = payload["metadata"]
    classes = meta.get("classes", [])
    if meta.get("architecture") != "ResNet18" or len(classes) < 2 or len(set(classes)) != len(classes):
        raise ValueError("Checkpoint architecture/classes are invalid")
    if meta.get("class_to_idx") != {name: i for i, name in enumerate(classes)}:
        raise ValueError("Checkpoint class mapping mismatch")
    for field in ["version", "manifest_sha256", "validation_scope", "normalization"]:
        if not meta.get(field):
            raise ValueError(f"Missing checkpoint metadata: {field}")
    if meta["normalization"] not in ["batchnorm", "groupnorm"]:
        raise ValueError("Unsupported normalization")
    transform = preprocessing(meta["preprocessing"])
    model = build_resnet18(len(classes))
    if meta["normalization"] == "groupnorm":
        model = use_group_norm(model)
    model.load_state_dict(payload["state_dict"], strict=True)
    model.eval()
    return model, meta, transform


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

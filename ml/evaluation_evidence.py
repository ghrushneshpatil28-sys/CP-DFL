"""Publish measured evaluation tied to the exact selected checkpoint.

An absent, mismatched or inconsistent evaluation must never become a dashboard
percentage. No target threshold participates in these calculations.
"""
from datetime import datetime, timezone
import json
import math
import hashlib
from pathlib import Path


def checkpoint_digest(path):
    # Read-only dashboard evidence must not initialize PyTorch/torchvision.
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_metrics(metrics, classes):
    matrix = metrics["confusion_matrix"]
    n = len(classes)
    if (len(matrix) != n or any(len(row) != n for row in matrix)
            or any(type(value) is not int or value < 0 for row in matrix for value in row)):
        raise ValueError("Invalid evaluation confusion matrix")
    count = sum(map(sum, matrix))
    if count <= 0 or type(metrics["sample_count"]) is not int or metrics["sample_count"] != count:
        raise ValueError("Evaluation sample count mismatch")
    recall, precision, f1 = [], [], []
    for i, label in enumerate(classes):
        tp = matrix[i][i]
        support, predicted = sum(matrix[i]), sum(row[i] for row in matrix)
        r = tp / support if support else 0.
        p = tp / predicted if predicted else 0.
        recall.append(r)
        precision.append(p)
        f1.append(2 * p * r / (p + r) if p + r else 0.)
        if metrics["per_class"][label]["support"] != support:
            raise ValueError("Evaluation class support mismatch")
    computed = {"accuracy": sum(matrix[i][i] for i in range(n)) / count,
                "macro_precision": sum(precision) / n, "macro_recall": sum(recall) / n,
                "macro_f1": sum(f1) / n,
                "balanced_accuracy": sum(r for r, row in zip(recall, matrix) if sum(row)) / sum(bool(sum(row)) for row in matrix)}
    for name, actual in computed.items():
        if not math.isclose(metrics[name], actual, rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError(f"Evaluation {name} does not match confusion matrix")
    if metrics.get("roc_auc") is not None and not 0 <= metrics["roc_auc"] <= 1:
        raise ValueError("Evaluation ROC-AUC out of range")


def build_evidence(checkpoint, results_path):
    from ml.checkpoints import load_checkpoint
    checkpoint, results_path = Path(checkpoint).resolve(), Path(results_path).resolve()
    _, meta, _ = load_checkpoint(checkpoint)
    result = json.loads(results_path.read_text(encoding="utf-8"))
    digest = checkpoint_digest(checkpoint)
    if (Path(result["checkpoint"]).resolve() != checkpoint
            or result.get("checkpoint_sha256", digest) != digest
            or result["manifest_sha256"] != meta["manifest_sha256"]
            or result["classes"] != meta["classes"]
            or result["algorithm"] != meta["algorithm"]
            or result["image_size"] != meta["preprocessing"]["image_size"]):
        raise ValueError("Checkpoint/evaluation provenance mismatch")
    validate_metrics(result["test"], meta["classes"])
    return {"schema_version": 1, "status": "verified", "architecture": "ResNet18",
            "model_version": meta["version"], "checkpoint_sha256": digest,
            "manifest_sha256": meta["manifest_sha256"], "classes": meta["classes"],
            "image_size": meta["preprocessing"]["image_size"], "normalization": meta["normalization"],
            "algorithm": meta["algorithm"], "test": result["test"],
            "best_round": meta["best_round"], "rounds_completed": result["rounds_completed"],
            "validation_scope": meta["validation_scope"],
            "dp_enabled": meta["training_config"].get("dp", {}).get("enabled", False),
            "secure_aggregation_enabled": meta["training_config"].get("secure_aggregation", False),
            "evidence_recorded_at": datetime.now(timezone.utc).isoformat(),
            "notice": "Measured on a previously used research test split; patient independence and external clinical validity remain unverified."}


def read_selected_evaluation(checkpoint):
    checkpoint = Path(checkpoint)
    try:
        evidence = json.loads(checkpoint.with_suffix(".evaluation.json").read_text(encoding="utf-8"))
        if evidence.get("schema_version") != 1 or evidence.get("architecture") != "ResNet18" or evidence.get("status") != "verified":
            raise ValueError("Invalid evaluation evidence")
        if checkpoint_digest(checkpoint) != evidence["checkpoint_sha256"]:
            raise ValueError("Evaluation belongs to a different checkpoint")
        validate_metrics(evidence["test"], evidence["classes"])
        return evidence
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError):
        return {"status": "unavailable", "architecture": "ResNet18",
                "reason": "No verified evaluation matches the selected checkpoint. Accuracy is not available."}

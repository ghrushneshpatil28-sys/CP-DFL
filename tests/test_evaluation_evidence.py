import copy
import json
import pytest
import torch
from fastapi.testclient import TestClient

from ml.checkpoints import file_sha256
from ml.evaluation_evidence import build_evidence, read_selected_evaluation, validate_metrics
from ml.metrics import classification_metrics


def evaluation_fixture(app, tmp_path):
    """Synthetic metrics ONLY for contract tests, never production evidence."""
    checkpoint = app.state.checkpoint
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    meta = payload["metadata"]
    meta.update(algorithm="centralized", best_round=1, training_config={"dp": {"enabled": False}})
    torch.save(payload, checkpoint)
    classes = meta["classes"]
    labels, predicted = [0, 0, 0, 0, 1, 1], [0, 0, 0, 1, 1, 1]
    probs = [[.9, .1] if p == 0 else [.1, .9] for p in predicted]
    metrics = classification_metrics(labels, probs, classes)
    result = {"checkpoint": str(checkpoint), "checkpoint_sha256": file_sha256(checkpoint),
              "manifest_sha256": meta["manifest_sha256"], "classes": classes,
              "algorithm": meta["algorithm"], "image_size": meta["preprocessing"]["image_size"],
              "test": metrics, "rounds_completed": 1}
    path = tmp_path / "results.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    return checkpoint, path, result


def test_selected_evaluation_authorized_and_bound_to_model(app, clients, tmp_path):
    admin, doctor, _ = clients
    route = "/api/model/evaluation"
    assert TestClient(app).get(route).status_code == 401
    assert doctor.get(route).json()["status"] == "unavailable"
    checkpoint, path, result = evaluation_fixture(app, tmp_path)
    evidence = build_evidence(checkpoint, path)
    checkpoint.with_suffix(".evaluation.json").write_text(json.dumps(evidence), encoding="utf-8")
    for client in (admin, doctor):
        response = client.get(route)
        assert response.status_code == 200
        assert response.json()["test"]["accuracy"] == result["test"]["accuracy"] == pytest.approx(5 / 6)
        assert response.json()["model_version"] == "test-only-untrained"
    # An older model's metrics cannot be reused after a file change.
    with checkpoint.open("ab") as stream:
        stream.write(b"different-checkpoint")
    assert admin.get(route).json()["status"] == "unavailable"


def test_fabricated_accuracy_rejected_even_with_correct_checkpoint(app, tmp_path):
    checkpoint, path, result = evaluation_fixture(app, tmp_path)
    result["test"]["accuracy"] = .99
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="accuracy"):
        build_evidence(checkpoint, path)


@pytest.mark.parametrize("field", ["checkpoint_sha256", "manifest_sha256", "classes", "image_size"])
def test_evaluation_provenance_mismatches_rejected(app, tmp_path, field):
    checkpoint, path, result = evaluation_fixture(app, tmp_path)
    result[field] = "mismatched"
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        build_evidence(checkpoint, path)


def test_accuracy_is_not_clamped_to_a_target(app, tmp_path):
    checkpoint, path, result = evaluation_fixture(app, tmp_path)
    metrics = classification_metrics([0, 0, 0, 1, 1, 1], [[.1, .9]] * 6, result["classes"])
    result["test"] = metrics
    path.write_text(json.dumps(result), encoding="utf-8")
    evidence = build_evidence(checkpoint, path)
    assert evidence["test"]["accuracy"] == .5
    corrupt = copy.deepcopy(metrics)
    corrupt["sample_count"] = 1
    with pytest.raises(ValueError, match="sample count"):
        validate_metrics(corrupt, result["classes"])
    checkpoint.with_suffix(".evaluation.json").write_text('{"accuracy":99}', encoding="utf-8")
    assert read_selected_evaluation(checkpoint)["status"] == "unavailable"

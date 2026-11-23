import copy
import hashlib
import json

import pytest
import torch
from PIL import Image

from ml.checkpoints import DEFAULT_PREPROCESS, load_checkpoint, preprocessing, save_checkpoint
from ml.dataset import create_manifest, group_rows, scan, verify_manifest
from ml.federated import aggregate, partition_clients, proximal_loss
from ml.gradcam import gradcam
from ml.models import build_resnet18
from ml.models.resnet18 import use_group_norm


def test_resnet_identity_output_and_gradcam():
    model = build_resnet18(4).eval()
    assert type(model).__name__ == "ResNet" and len(model.layer1) == len(model.layer4) == 2
    x = torch.randn(1, 3, 64, 64)
    assert model(x).shape == (1, 4)
    before = len(model.layer4._forward_hooks)
    overlay, probabilities = gradcam(model, x, Image.new("RGB", (64, 64)))
    assert overlay.size == (64, 64) and sum(probabilities) == pytest.approx(1.)
    assert len(model.layer4._forward_hooks) == before


def test_checkpoint_strictness(tmp_path):
    path = tmp_path / "model.pt"
    model = build_resnet18(2)
    torch.save(model.state_dict(), path)
    with pytest.raises(ValueError, match="Legacy"):
        load_checkpoint(path)
    meta = {"architecture": "ResNet18", "classes": ["a", "b"], "class_to_idx": {"a": 0, "b": 1},
            "version": "test", "normalization": "batchnorm", "manifest_sha256": "abc",
            "validation_scope": "test", "preprocessing": DEFAULT_PREPROCESS}
    save_checkpoint(path, model, meta)
    loaded, metadata, transform = load_checkpoint(path)
    assert loaded.fc.out_features == 2 and metadata["classes"] == ["a", "b"]
    image = Image.new("RGB", (100, 80))
    assert torch.equal(transform(image), preprocessing(DEFAULT_PREPROCESS)(image))
    save_checkpoint(path, model, {**meta, "class_to_idx": {"a": 1, "b": 0}})
    with pytest.raises(ValueError, match="mapping"):
        load_checkpoint(path)
    save_checkpoint(path, build_resnet18(3), meta)
    with pytest.raises(RuntimeError):
        load_checkpoint(path)


def rows_fixture(count=60):
    return [{"path": f"{i}.png", "label": ["a", "b"][i % 2], "sha256": str(i), "pixel_sha256": str(i),
             "patient_id": f"p{i // 2}", "study_id": "", "original_split": "pool", "group_id": str(i // 2)} for i in range(count)]


def test_dataset_hashes_and_reproducibility(tmp_path):
    source = tmp_path / "data"
    (source / "train/a").mkdir(parents=True)
    (source / "test/a").mkdir(parents=True)
    image = Image.new("RGB", (64, 64), (10, 10, 10))
    image.save(source / "train/a/one.png")
    image.save(source / "test/a/two.png", compress_level=0)
    rows, invalid = scan(source)
    assert not invalid and rows[0]["sha256"] != rows[1]["sha256"]
    assert rows[0]["pixel_sha256"] == rows[1]["pixel_sha256"]
    assert len(group_rows(rows)) == 1
    rows = rows_fixture()
    first = create_manifest(rows, preserve_test=False)
    assert first == create_manifest(rows, preserve_test=False)
    assert first != create_manifest(rows, seed=43, preserve_test=False)
    verify_manifest(first)
    corrupted = copy.deepcopy(first)
    same_patient = next(i for i in range(1, len(corrupted)) if corrupted[i]["patient_id"] == corrupted[0]["patient_id"])
    corrupted[same_patient]["split"] = "test" if corrupted[0]["split"] != "test" else "train"
    with pytest.raises(ValueError, match="overlap"):
        verify_manifest(corrupted)


def test_fedavg_prox_and_malformed_updates():
    states = [(1, {"w": torch.tensor([1., 2.])}), (2, {"w": torch.tensor([3., 4.])}), (1, {"w": torch.tensor([5., 6.])})]
    assert torch.equal(aggregate(states)["w"], torch.tensor([3., 4.]))
    with pytest.raises(ValueError, match="three"):
        aggregate(states[:2])
    with pytest.raises(ValueError, match="Invalid"):
        aggregate([*states[:2], (1, {"w": torch.tensor([float("nan"), 1.])})])
    with pytest.raises(ValueError):
        aggregate([*states[:2], (1, {"w": torch.ones(3)})])
    model = torch.nn.Linear(2, 1, bias=False)
    initial = [p.detach().clone() for p in model.parameters()]
    with torch.no_grad():
        model.weight.add_(1)
    assert proximal_loss(model, initial, .1).item() == pytest.approx(.1)


def test_non_iid_groups():
    rows = [{**r, "split": "train"} for r in rows_fixture()]
    clients = partition_clients(rows, seed=42, alpha=.1)
    assert clients == partition_clients(rows, seed=42, alpha=.1)
    assert len(clients) == 3 and all(clients.values())
    seen = {}
    for name, assigned in clients.items():
        for row in assigned:
            assert row["patient_id"] not in seen or seen[row["patient_id"]] == name
            seen[row["patient_id"]] = name
    assert sum(map(len, clients.values())) == len(rows)


def test_actual_dp_sgd_and_composition():
    from opacus.validators import ModuleValidator
    from ml.engine import train_local
    from torch.utils.data import DataLoader, TensorDataset
    model = use_group_norm(build_resnet18(2))
    assert not ModuleValidator.validate(model, strict=False)
    data = DataLoader(TensorDataset(torch.randn(4, 3, 32, 32), torch.tensor([0, 1, 0, 1])), batch_size=2)
    config = {"algorithm": "fedavg", "learning_rate": .001, "local_epochs": 1,
              "dp": {"enabled": True, "noise_multiplier": 1.1, "max_grad_norm": 1., "delta": 1e-5}}
    model, first, accountant = train_local(model, data, config)
    assert first["privacy"]["epsilon"] > 0 and first["steps"] == 2
    assert first["loss"] is None
    _, second, _ = train_local(model, data, config, accountant_state=accountant)
    assert second["privacy"]["epsilon"] > first["privacy"]["epsilon"]
    assert second["privacy"]["sample_rate"] == .5

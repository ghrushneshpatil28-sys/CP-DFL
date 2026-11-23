import json
from pathlib import Path

from sqlalchemy import select
import pytest

from backend.models import Experiment, RoundMetric, PrivacyMetric
from backend.worker import execute
from ml.dataset import ROOT


@pytest.mark.parametrize("algorithm,secure,private", [("fedprox", False, False), ("fedavg", True, False), ("fedprox", True, True)])
def test_three_clients_actual_training_and_persistence(app, tmp_path, algorithm, secure, private):
    manifest = json.loads((ROOT / "ml/data/manifest.json").read_text(encoding="utf-8"))
    subset = []
    for split in ["train", "val", "test"]:
        for label in manifest["classes"]:
            subset.extend([r for r in manifest["rows"] if r["split"] == split and r["label"] == label][:3])
    manifest["rows"] = subset
    path = tmp_path / "small-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    config = {"algorithm": algorithm, "rounds": 2 if private else 1, "local_epochs": 1, "batch_size": 2, "image_size": 64,
              "learning_rate": .001, "optimizer": "sgd", "seed": 42, "alpha": .5, "mu": .01, "patience": 2,
              "dp": {"enabled": private}, "secure_aggregation": secure, "manifest": str(path), "threads": 2}
    with app.state.sessions() as db:
        row = Experiment(algorithm=algorithm, config=config, status="running")
        db.add(row); db.commit(); experiment_id = row.id
    execute(experiment_id, app.state.sessions, output_root=tmp_path / "experiments")
    with app.state.sessions() as db:
        row = db.get(Experiment, experiment_id)
        assert row.status == "completed", row.error
        metrics = db.scalar(select(RoundMetric).where(RoundMetric.experiment_id == experiment_id))
        assert len(metrics.metrics["clients"]) == 3
        assert metrics.metrics["communication_bytes"] > 0
        assert Path(row.results["checkpoint"]).is_file()
        if secure:
            assert row.results["secure_aggregation"]["status"] == "completed"
            assert metrics.metrics["local_loss"] is None
            assert all(client["loss"] is None for client in metrics.metrics["clients"].values())
            assert all(info["class_distribution_withheld"] for info in metrics.metrics["distributions"].values())
            assert metrics.metrics["communication_bytes"] == sum(metrics.metrics["secure_aggregation"][key] for key in ["bytes_sent", "bytes_received"])
        if private:
            ledger = list(db.scalars(select(PrivacyMetric).where(PrivacyMetric.experiment_id == experiment_id)))
            assert len(ledger) == 6
            for name in ["Hospital A", "Hospital B", "Hospital C"]:
                entries = [item.metrics for item in ledger if item.client == name]
                assert entries[1]["cumulative_steps"] > entries[0]["cumulative_steps"]
                assert entries[1]["epsilon"] > entries[0]["epsilon"] > 0

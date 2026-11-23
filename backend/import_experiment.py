"""Import actual CLI experiment artifacts into the dashboard database."""
import argparse
import json
from pathlib import Path

from sqlalchemy import select

from backend.bootstrap import initialize
from backend.database import make_database
from backend.models import AuditLog, Experiment, PrivacyMetric, RoundMetric, now
from ml.checkpoints import load_checkpoint, file_sha256


def import_directory(directory, sessions):
    directory = Path(directory).resolve()
    bundle = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    rounds = [json.loads(line) for line in (directory / "rounds.jsonl").read_text(encoding="utf-8").splitlines()]
    _, meta, _ = load_checkpoint(directory / "best.pt")
    if bundle["config"].get("secure_aggregation"):
        from ml.secure_aggregation import PROTOCOL
        for item in [result, *rounds]:
            evidence = item.get("secure_aggregation")
            if not isinstance(evidence, dict) or evidence.get("protocol") != PROTOCOL or evidence.get("status") != "completed" or evidence.get("individual_updates_visible") is not False:
                raise ValueError("Secure aggregation artifact lacks completed protocol evidence")
        if meta["normalization"] != "groupnorm" or not meta["training_config"].get("secure_aggregation"):
            raise ValueError("Secure aggregation checkpoint contract mismatch")
    if bundle["config"].get("dp", {}).get("enabled") and meta.get("privacy_randomness") != "independent-entropy-seeded-prng":
        raise ValueError("DP artifact predates independent noise/sampling entropy; not eligible for privacy reporting")
    if bundle["config"].get("dp", {}).get("enabled") and any(local.get("loss") is not None for r in rounds for local in r["clients"].values()):
        raise ValueError("DP artifact discloses unaccounted raw local losses; retrain with the hardened pipeline")
    if result["manifest_sha256"] != meta["manifest_sha256"] or result["classes"] != meta["classes"] or len(rounds) != result["rounds_completed"]:
        raise ValueError("Experiment artifacts are inconsistent")
    if file_sha256(bundle["config"]["manifest"]) != meta["manifest_sha256"]:
        raise ValueError("Experiment dataset manifest changed")
    with sessions() as db:
        if db.get(Experiment, directory.name):
            return directory.name
        row = Experiment(id=directory.name, algorithm=result["algorithm"], config=bundle["config"], results=result,
                         status="completed", completed_at=now())
        db.add(row)
        db.flush()
        for metric in rounds:
            db.add(RoundMetric(experiment_id=row.id, round_number=metric["round"], metrics=metric))
            for client, local in metric["clients"].items():
                if local.get("privacy"):
                    db.add(PrivacyMetric(experiment_id=row.id, round_number=metric["round"], client=client, metrics=local["privacy"]))
        db.add(AuditLog(action="experiment.imported", resource=row.id))
        db.commit()
        return row.id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    engine, sessions = make_database()
    initialize(engine, sessions)
    print(import_directory(args.directory, sessions))


if __name__ == "__main__":
    main()

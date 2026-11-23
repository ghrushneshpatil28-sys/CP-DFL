"""Single-worker persistent queue; run separately from the API process."""
import argparse
import time
import traceback

from sqlalchemy import select, update

from backend.bootstrap import initialize
from backend.database import ROOT, make_database
from backend.models import AuditLog, Experiment, PrivacyMetric, RoundMetric, now


def execute(experiment_id, sessions, output_root=None):
    from ml.engine import run_experiment
    with sessions() as db:
        row = db.get(Experiment, experiment_id)
        config = row.config

    def persist_round(metrics):
        with sessions() as db:
            db.add(RoundMetric(experiment_id=experiment_id, round_number=metrics["round"], metrics=metrics))
            for name, local in metrics["clients"].items():
                if local.get("privacy"):
                    db.add(PrivacyMetric(experiment_id=experiment_id, round_number=metrics["round"], client=name, metrics=local["privacy"]))
            db.commit()

    try:
        result = run_experiment(config, (output_root or ROOT / "ml/outputs/experiments") / experiment_id, persist_round)
        with sessions() as db:
            row = db.get(Experiment, experiment_id)
            row.status, row.results, row.completed_at = "completed", result, now()
            db.add(AuditLog(action="experiment.completed", resource=experiment_id))
            db.commit()
    except Exception as error:
        traceback.print_exc()
        with sessions() as db:
            row = db.get(Experiment, experiment_id)
            row.status, row.error, row.completed_at = "failed", str(error), now()
            db.add(AuditLog(action="experiment.failed", resource=experiment_id))
            db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--recover-interrupted", action="store_true", help="Only when no other worker is running")
    args = parser.parse_args()
    engine, sessions = make_database()
    initialize(engine, sessions)
    if args.recover_interrupted:
        with sessions() as db:
            db.execute(update(Experiment).where(Experiment.status == "running").values(status="failed", error="Worker interrupted; start a new experiment", completed_at=now()))
            db.commit()
    while True:
        with sessions() as db:
            row = db.scalar(select(Experiment).where(Experiment.status == "queued").order_by(Experiment.created_at))
            experiment_id = row.id if row else None
            if experiment_id:
                claimed = db.execute(update(Experiment).where(Experiment.id == experiment_id, Experiment.status == "queued").values(status="running"))
                db.commit()
                if claimed.rowcount != 1:
                    experiment_id = None
        if experiment_id:
            execute(experiment_id, sessions)
        if args.once:
            break
        time.sleep(2)


if __name__ == "__main__":
    main()

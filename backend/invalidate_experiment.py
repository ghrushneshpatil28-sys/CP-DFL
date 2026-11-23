"""Preserve flawed experiment evidence while excluding it from valid comparisons/budgets."""
import argparse
from backend.database import make_database
from backend.models import AuditLog, Experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    _, sessions = make_database()
    with sessions() as db:
        row = db.get(Experiment, args.id)
        if not row:
            parser.error("Experiment not found")
        row.status, row.error = "invalidated", args.reason
        db.add(AuditLog(action="experiment.invalidated", resource=row.id))
        db.commit()


if __name__ == "__main__":
    main()

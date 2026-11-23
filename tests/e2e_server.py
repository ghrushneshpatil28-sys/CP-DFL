"""Isolated browser-test server. Never run as the production application."""
import uuid
from pathlib import Path

from backend.bootstrap import initialize
from backend.database import ROOT, make_database
from backend.import_experiment import import_directory
from backend.main import create_app
from backend.models import User, DoctorProfile
from backend.security import password_hash

test_root = ROOT / ".test-tmp/e2e" / uuid.uuid4().hex
test_root.mkdir(parents=True)
url = f"sqlite:///{(test_root / 'browser.db').as_posix()}"
engine, sessions = make_database(url)
initialize(engine, sessions)
with sessions() as db:
    for role, email in [("Admin", "admin@e2e.test"), ("Doctor", "doctor@e2e.test")]:
        row = User(name="Test " + role, email=email, role=role, password_hash=password_hash("browser-test-only-123"))
        db.add(row); db.flush()
        if role == "Doctor":
            db.add(DoctorProfile(user_id=row.id, specialty="Research", hospital="Test Hospital"))
    db.commit()
for name in ["centralized-verification", "fedavg-flower", "fedprox-flower", "fedavg-dp-entropy", "secagg-verification"]:
    path = ROOT / "ml/outputs/experiments" / name
    if (path / "results.json").is_file():
        import_directory(path, sessions)
app = create_app(url, test_root / "storage", ROOT / "ml/saved_models/approved.pt")

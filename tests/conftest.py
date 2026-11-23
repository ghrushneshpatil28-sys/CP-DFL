import io
import os
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import create_app
from backend.models import DoctorProfile, User
from backend.security import password_hash
from ml.checkpoints import DEFAULT_PREPROCESS, save_checkpoint
from ml.models import build_resnet18

torch.set_num_threads(2)


@pytest.fixture
def image_bytes():
    out = io.BytesIO()
    Image.new("RGB", (64, 64), (80, 80, 80)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def app(tmp_path):
    checkpoint = tmp_path / "fixture.pt"
    # Random weights ONLY in isolated tests. Never used by the application or evaluation artifacts.
    classes = ["Class A", "Class B"]
    save_checkpoint(checkpoint, build_resnet18(2), {"architecture": "ResNet18", "classes": classes,
        "class_to_idx": {c: i for i, c in enumerate(classes)}, "version": "test-only-untrained",
        "manifest_sha256": "test-fixture", "normalization": "batchnorm", "validation_scope": "synthetic test only",
        "preprocessing": {**DEFAULT_PREPROCESS, "image_size": 64}})
    application = create_app(f"sqlite:///{(tmp_path / 'test.db').as_posix()}", tmp_path / "storage", checkpoint)
    with TestClient(application):
        with application.state.sessions() as db:
            for role, email in [("Admin", "admin@test.org"), ("Doctor", "one@test.org"), ("Doctor", "two@test.org")]:
                user = User(role=role, email=email, name=email.split("@")[0], password_hash=password_hash("test-password-123"))
                db.add(user)
                db.flush()
                if role == "Doctor":
                    db.add(DoctorProfile(user_id=user.id))
            db.commit()
        yield application


@pytest.fixture
def clients(app):
    result = []
    for email in ["admin@test.org", "one@test.org", "two@test.org"]:
        client = TestClient(app)
        response = client.post("/api/auth/login", json={"email": email, "password": "test-password-123"})
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        result.append(client)
    yield result
    for client in result:
        client.close()


@pytest.fixture
def patient_data():
    return {"full_name": "Test Patient", "date_of_birth": "1980-01-01", "sex": "Female", "smoking_status": "Never"}

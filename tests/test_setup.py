import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.main import create_app
from backend.models import User


@pytest.fixture
def first_run(tmp_path):
    app = create_app(f"sqlite:///{(tmp_path / 'setup.db').as_posix()}", tmp_path / "storage", allow_setup=True)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        yield app, client


def test_first_admin_setup_and_login(first_run):
    app, client = first_run
    status = client.get("/api/setup/status").json()
    assert status["required"] and status["enabled"] and status["setup_token"]
    body = {"name": "First Admin", "email": "admin@setup.test", "password": "my chosen password", "setup_token": status["setup_token"]}
    assert client.post("/api/setup/admin", json={**body, "setup_token": "x" * 48}).status_code == 403
    response = client.post("/api/setup/admin", json=body)
    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == "Admin"
    assert client.get("/api/auth/me").status_code == 200
    assert not client.get("/api/setup/status").json()["required"]
    assert client.get("/api/setup/status").json()["setup_token"] is None
    assert client.post("/api/setup/admin", json=body).status_code == 409
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_setup_disabled_by_default_and_for_nonlocal_clients(tmp_path):
    url = f"sqlite:///{(tmp_path / 'blocked.db').as_posix()}"
    app = create_app(url, tmp_path / "storage", allow_setup=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/setup/status").json() == {"required": True, "enabled": False, "setup_token": None}
    app.state.setup_enabled = True
    with TestClient(app, client=("203.0.113.5", 50000)) as client:
        assert not client.get("/api/setup/status").json()["enabled"]
        body = {"name": "Blocked Admin", "email": "blocked@setup.test", "password": "blocked-password-123", "setup_token": app.state.setup_token}
        assert client.post("/api/setup/admin", json=body).status_code == 403

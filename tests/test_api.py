import io
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select

from backend.models import Patient, User, AuditLog


def test_roles_csrf_logout_and_disabled(app, clients):
    admin, doctor, other = clients
    assert TestClient(app).get("/api/patients").status_code == 401
    assert doctor.get("/api/admin/doctors").status_code == 403
    assert admin.get("/api/patients").status_code == 403
    csrf = doctor.headers.pop("X-CSRF-Token")
    assert doctor.post("/api/auth/logout").status_code == 403
    doctor.headers["X-CSRF-Token"] = csrf
    assert doctor.post("/api/auth/logout").status_code == 200
    assert doctor.get("/api/auth/me").status_code == 401
    target = next(row for row in admin.get("/api/admin/doctors").json() if row["email"] == "two@test.org")
    assert admin.patch(f"/api/admin/doctors/{target['id']}/status", json={"active": False}).status_code == 200
    assert other.get("/api/auth/me").status_code == 401
    assert other.post("/api/auth/login", json={"email": "two@test.org", "password": "test-password-123"}).status_code == 401


def test_doctor_management(clients):
    admin, doctor, _ = clients
    payload = {"email": "new@test.org", "name": "New Doctor", "password": "strong-password-123", "hospital": "Research Hospital"}
    created = admin.post("/api/admin/doctors", json=payload)
    assert created.status_code == 201, created.text
    assert "password_hash" not in created.json()
    assert admin.post("/api/admin/doctors", json=payload).status_code == 409
    assert doctor.post("/api/admin/doctors", json=payload).status_code == 403
    assert admin.post("/api/admin/doctors", json={**payload, "role": "Patient"}).status_code == 422
    assert admin.patch(f"/api/admin/doctors/{created.json()['id']}", json={"name": "Edited Doctor"}).json()["name"] == "Edited Doctor"
    from backend.api_schemas import Login
    assert Login(email="test@test.org", password="  password with spaces  ").password == "  password with spaces  "


def test_patient_persistence_search_and_isolation(app, clients, patient_data):
    admin, doctor, other = clients
    response = doctor.post("/api/patients", json=patient_data)
    assert response.status_code == 201, response.text
    patient_id = response.json()["id"]
    assert doctor.patch(f"/api/patients/{patient_id}", json={"symptoms": "Persistent cough"}).json()["symptoms"] == "Persistent cough"
    assert doctor.get("/api/patients?q=Test&smoking_status=Never").json()["total"] == 1
    assert doctor.get("/api/patients?q=%").json()["total"] == 0
    assert other.get(f"/api/patients/{patient_id}").status_code == 404
    assert other.patch(f"/api/patients/{patient_id}", json={"full_name": "Stolen"}).status_code == 404
    assert other.get("/api/patients").json()["total"] == 0
    assert admin.get(f"/api/patients/{patient_id}").status_code == 403
    assert doctor.patch(f"/api/patients/{patient_id}", json={"full_name": None}).status_code == 422
    assert doctor.post(f"/api/patients/{patient_id}/visits", json={"notes": "Reviewed", "follow_up_date": "2026-12-01"}).status_code == 201
    assert len(doctor.get(f"/api/patients/{patient_id}/visits").json()) == 1
    assert len(doctor.get(f"/api/patients/{patient_id}/history").json()) == 2
    with app.state.sessions() as db:
        assert db.get(Patient, patient_id).symptoms == "Persistent cough"
    audit = admin.get("/api/admin/audit").json()
    assert all(row["resource"] == "protected" for row in audit if row["action"].startswith("patient."))


def test_upload_analysis_gradcam_reports(app, clients, patient_data, image_bytes, tmp_path):
    admin, doctor, other = clients
    patient = doctor.post("/api/patients", json=patient_data).json()
    base = f"/api/patients/{patient['id']}"
    assert doctor.post(base + "/images", files={"image": ("fake.png", b"not an image", "image/png")}).status_code == 422
    assert doctor.post(base + "/images", files={"image": ("wrong.jpg", image_bytes, "image/jpeg")}).status_code == 415
    assert other.post(base + "/images", files={"image": ("scan.png", image_bytes, "image/png")}).status_code == 404
    uploaded = doctor.post(base + "/images", files={"image": ("scan.png", image_bytes, "image/png")})
    assert uploaded.status_code == 201, uploaded.text
    image = uploaded.json()
    assert "storage_key" not in image
    assert doctor.get(image["url"]).status_code == 200
    assert other.get(image["url"]).status_code == 404
    assert admin.get(image["url"]).status_code == 403
    response = doctor.post(base + "/analyze", json={"image_id": image["id"]})
    assert response.status_code == 201, response.text
    analysis = response.json()
    assert analysis["result"]["architecture"] == "ResNet18"
    assert abs(sum(analysis["result"]["probabilities"].values()) - 1) < 1e-5
    assert doctor.get(analysis["heatmap_url"]).headers["content-type"] == "image/png"
    assert other.get(f"/api/analyses/{analysis['id']}").status_code == 404
    review = {"observations": "Doctor review: research fixture only. " * 100, "follow_up": "Review symptoms at the next visit."}
    assert doctor.patch(f"/api/analyses/{analysis['id']}", json=review).status_code == 200
    report_response = doctor.post(base + "/reports", json={"analysis_id": analysis["id"]})
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()
    pdf = doctor.get(report["download_url"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert other.get(report["download_url"]).status_code == 404
    assert admin.get(report["download_url"]).status_code == 403
    reader = PdfReader(io.BytesIO(pdf.content))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert patient["id"] in text and "ResNet18" in text and "not a confirmed" in text
    assert "next visit" in text
    assert len(doctor.get(base + "/reports").json()) == 1
    assert len(doctor.get(base + "/analyses").json()) == 1
    assert other.get("/api/analyses").json() == []
    # Non-identifiable synthetic report retained only when explicitly requested for visual QA.
    import os
    if os.environ.get("REPORT_QA_OUTPUT"):
        Path(os.environ["REPORT_QA_OUTPUT"]).write_bytes(pdf.content)


def test_missing_checkpoint_is_explicit(app, clients, patient_data, image_bytes):
    _, doctor, _ = clients
    patient = doctor.post("/api/patients", json=patient_data).json()
    base = f"/api/patients/{patient['id']}"
    image = doctor.post(base + "/images", files={"image": ("scan.png", image_bytes, "image/png")}).json()
    app.state.checkpoint = Path("missing-checkpoint.pt")
    response = doctor.post(base + "/analyze", json={"image_id": image["id"]})
    assert response.status_code == 503 and "no prediction" in response.json()["detail"]
    assert doctor.get(base + "/analyses").json() == []


def test_experiment_permissions_and_privacy(clients):
    admin, doctor, _ = clients
    assert doctor.post("/api/admin/federated/experiments", json={}).status_code == 403
    assert admin.post("/api/admin/federated/experiments", json={"secure_aggregation": True, "algorithm": "centralized"}).status_code == 422
    assert admin.post("/api/admin/federated/experiments", json={"algorithm": "other"}).status_code == 422
    assert len(admin.get("/api/admin/federated/clients").json()) == 3
    privacy = admin.get("/api/admin/federated/privacy").json()
    assert privacy["capabilities"]["secure_aggregation"]["status"] == "Implemented / local"
    assert privacy["secure_rounds"] == []
    assert privacy["metrics"] == []
    queued = admin.post("/api/admin/federated/experiments", json={"secure_aggregation": True})
    assert queued.status_code == 201 and queued.json()["config"]["secure_aggregation"] is True


def test_login_throttle_and_upload_size(clients, patient_data):
    _, doctor, _ = clients
    for _ in range(10):
        assert doctor.post('/api/auth/login', json={"email": "absent@test.org", "password": "wrong"}).status_code == 401
    assert doctor.post('/api/auth/login', json={"email": "absent@test.org", "password": "wrong"}).status_code == 429
    patient = doctor.post('/api/patients', json=patient_data).json()
    assert doctor.post(f"/api/patients/{patient['id']}/images", files={"image": ('large.png', b'x' * (10 * 1024 * 1024 + 1), 'image/png')}).status_code == 413

"""Authenticated research application. Run from repository root: uvicorn backend.main:app."""
from contextlib import asynccontextmanager
from datetime import date
import hmac
import ipaddress
import os
from pathlib import Path
import secrets
import threading
import time

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from backend import api_schemas as s
from backend.bootstrap import initialize
from backend.database import ROOT, make_database
from backend.models import (Analysis, AuditLog, ClinicalHistory, DoctorProfile, Experiment, FederatedClient,
    LoginAttempt, MedicalImage, Patient, PrivacyMetric, Report, RoundMetric, Session, SetupState, User, Visit, now, uid)
from backend.security import (COOKIE, admin, audit, current_user, doctor, get_db, password_hash,
                              create_session, public_user, token_hash, verify_password)
from backend.storage import protected_path, validate_image

_dummy_hash = password_hash(secrets.token_urlsafe(24))
_experiment_lock = threading.Lock()


def serialize(obj, exclude=()):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns if column.name not in exclude}


def owned_patient(db, patient_id, user):
    patient = db.scalar(select(Patient).where(Patient.id == patient_id, Patient.doctor_id == user.id))
    if not patient:
        audit(db, user, "patient.access_denied")
        db.commit()
        raise HTTPException(404, "Patient not found")
    return patient


def owned_analysis(db, analysis_id, user):
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    owned_patient(db, analysis.patient_id, user)
    return analysis


def analysis_json(analysis):
    return {**serialize(analysis, ["heatmap_key"]), "heatmap_url": f"/api/analyses/{analysis.id}/heatmap",
            "image_url": f"/api/images/{analysis.image_id}/content"}


def create_app(database_url=None, storage_dir=None, checkpoint=None, allow_setup=None):
    engine, sessions = make_database(database_url)
    storage = Path(storage_dir or os.environ.get("STORAGE_DIR", ROOT / "backend/storage")).resolve()
    storage.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(application):
        initialize(engine, sessions)
        yield
        engine.dispose()

    app = FastAPI(title="Distributed Lung Cancer Research", version="3.0.0", lifespan=lifespan)
    app.state.sessions, app.state.storage = sessions, storage
    app.state.setup_enabled = allow_setup if allow_setup is not None else os.environ.get("ENABLE_LOCAL_SETUP", "false").lower() == "true"
    app.state.setup_token = secrets.token_urlsafe(48)
    app.state.checkpoint = Path(checkpoint or os.environ.get("MODEL_CHECKPOINT", ROOT / "ml/saved_models/approved.pt"))
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:7351,http://127.0.0.1:7351").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-CSRF-Token"])

    @app.middleware("http")
    async def security_headers(request, call_next):
        if request.method not in ["GET", "HEAD", "OPTIONS"] and request.headers.get("origin") and request.headers["origin"] not in origins:
            return Response("Origin not allowed", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health():
        return {"status": "ok", "application": "pulsar-research", "instance": os.environ.get("PULSAR_INSTANCE"),
                "architecture": "ResNet18", "research_only": True}

    def local_setup_allowed(request):
        if not app.state.setup_enabled or os.environ.get("COOKIE_SECURE", "false").lower() == "true":
            return False
        try:
            return ipaddress.ip_address(request.client.host).is_loopback
        except (ValueError, AttributeError):
            return False

    @api.get("/setup/status")
    def setup_status(request: Request, db=Depends(get_db)):
        required = db.scalar(select(func.count()).select_from(User)) == 0 and db.get(SetupState, "initial-admin") is None
        allowed = local_setup_allowed(request)
        return {"required": required, "enabled": allowed,
                "setup_token": app.state.setup_token if required and allowed else None}

    @api.post("/setup/admin", status_code=201)
    def setup_admin(data: s.AdminSetup, request: Request, response: Response, db=Depends(get_db)):
        if not local_setup_allowed(request):
            raise HTTPException(403, "Initial browser setup is available only through the local application launcher")
        if not hmac.compare_digest(data.setup_token, app.state.setup_token):
            raise HTTPException(403, "Invalid setup token; reload the setup page")
        # The fixed primary key serializes setup across processes as well as requests.
        db.add(SetupState(id="initial-admin"))
        try:
            db.flush()
            if db.scalar(select(func.count()).select_from(User)):
                db.rollback()
                raise HTTPException(409, "Initial setup has already been completed")
            user = User(email=data.email.lower(), name=data.name, role="Admin", password_hash=password_hash(data.password))
            db.add(user)
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Initial setup has already been completed")
        audit(db, user, "setup.completed")
        return create_session(db, user, request, response)

    @api.post("/auth/login")
    def login(data: s.Login, request: Request, response: Response, db=Depends(get_db)):
        email = data.email.lower()
        key = token_hash(email + "|" + (request.client.host if request.client else "local"))
        attempt = db.get(LoginAttempt, key)
        timestamp = time.time()
        if attempt and timestamp - attempt.window_start < 900 and attempt.count >= 10:
            raise HTTPException(429, "Too many login attempts. Try again after 15 minutes")
        if not attempt:
            attempt = LoginAttempt(key=key, count=0, window_start=timestamp)
            db.add(attempt)
        elif timestamp - attempt.window_start >= 900:
            attempt.count, attempt.window_start = 0, timestamp
        user = db.scalar(select(User).where(User.email == email))
        valid = verify_password(data.password, user.password_hash if user else _dummy_hash)
        if not user or not valid or not user.active:
            attempt.count += 1
            audit(db, None, "auth.login_failed")
            db.commit()
            raise HTTPException(401, "Invalid credentials or inactive account")
        attempt.count = 0
        return create_session(db, user, request, response)

    @api.get("/auth/me")
    def me(request: Request, user=Depends(current_user), db=Depends(get_db)):
        return {"user": public_user(user, db), "csrf_token": request.state.auth_session.csrf_token}

    @api.post("/auth/logout")
    def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
        db.delete(request.state.auth_session)
        audit(db, user, "auth.logout")
        db.commit()
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @api.patch("/auth/profile")
    def profile(data: s.DoctorUpdate, user=Depends(doctor), db=Depends(get_db)):
        update_doctor(db, user, data)
        audit(db, user, "doctor.profile_updated")
        db.commit()
        return public_user(user, db)

    @api.get("/admin/doctors")
    def doctors(user=Depends(admin), db=Depends(get_db)):
        return [public_user(row, db) for row in db.scalars(select(User).where(User.role == "Doctor").order_by(User.created_at.desc()))]

    @api.post("/admin/doctors", status_code=201)
    def add_doctor(data: s.DoctorCreate, user=Depends(admin), db=Depends(get_db)):
        account = User(email=data.email.lower(), name=data.name, password_hash=password_hash(data.password), role="Doctor")
        db.add(account)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Email already registered")
        db.add(DoctorProfile(user_id=account.id, specialty=data.specialty, hospital=data.hospital, registration=data.registration))
        audit(db, user, "doctor.created", account.id)
        db.commit()
        return public_user(account, db)

    @api.patch("/admin/doctors/{doctor_id}")
    def edit_doctor(doctor_id: str, data: s.DoctorUpdate, user=Depends(admin), db=Depends(get_db)):
        account = db.get(User, doctor_id)
        if not account or account.role != "Doctor":
            raise HTTPException(404, "Doctor not found")
        update_doctor(db, account, data)
        audit(db, user, "doctor.updated", account.id)
        db.commit()
        return public_user(account, db)

    @api.patch("/admin/doctors/{doctor_id}/status")
    def doctor_status(doctor_id: str, data: s.AccountStatus, user=Depends(admin), db=Depends(get_db)):
        account = db.get(User, doctor_id)
        if not account or account.role != "Doctor":
            raise HTTPException(404, "Doctor not found")
        account.active = data.active
        for session in db.scalars(select(Session).where(Session.user_id == account.id)):
            db.delete(session)
        audit(db, user, "doctor.activated" if data.active else "doctor.deactivated", account.id)
        db.commit()
        return public_user(account, db)

    @api.get("/patients")
    def patients(q: str = Query("", max_length=160), smoking_status: str | None = None,
                 sort: str = Query("updated_at", pattern="^(full_name|updated_at|follow_up_date)$"),
                 page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=100),
                 follow_up: bool = False, user=Depends(doctor), db=Depends(get_db)):
        query = select(Patient).where(Patient.doctor_id == user.id)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(or_(Patient.full_name.ilike(f"%{escaped}%", escape="\\"), Patient.id.ilike(f"%{escaped}%", escape="\\")))
        if smoking_status:
            query = query.where(Patient.smoking_status == smoking_status)
        if follow_up:
            query = query.where(Patient.follow_up_date.is_not(None))
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        order = getattr(Patient, sort)
        items = db.scalars(query.order_by(order.asc() if sort != "updated_at" else order.desc(), Patient.id).offset((page - 1) * page_size).limit(page_size))
        return {"items": [serialize(row) for row in items], "total": total, "page": page, "page_size": page_size}

    @api.post("/patients", status_code=201)
    def add_patient(data: s.PatientData, user=Depends(doctor), db=Depends(get_db)):
        patient = Patient(doctor_id=user.id, **data.model_dump(mode="json"))
        db.add(patient)
        db.flush()
        db.add(ClinicalHistory(patient_id=patient.id, doctor_id=user.id, snapshot=data.model_dump(mode="json")))
        audit(db, user, "patient.created", patient.id)
        db.commit()
        return serialize(patient)

    @api.get("/patients/{patient_id}")
    def patient_detail(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        patient = owned_patient(db, patient_id, user)
        audit(db, user, "patient.viewed", patient.id)
        db.commit()
        return serialize(patient)

    @api.patch("/patients/{patient_id}")
    def edit_patient(patient_id: str, data: s.PatientPatch, user=Depends(doctor), db=Depends(get_db)):
        patient = owned_patient(db, patient_id, user)
        before = {k: getattr(patient, k) for k in s.PatientData.model_fields}
        try:
            merged = s.PatientData(**{**before, **data.model_dump(exclude_unset=True, mode="json")})
        except ValidationError as error:
            raise HTTPException(422, str(error))
        for key, value in merged.model_dump(mode="json").items():
            setattr(patient, key, value)
        patient.updated_at = now()
        db.add(ClinicalHistory(patient_id=patient.id, doctor_id=user.id, snapshot=before))
        audit(db, user, "patient.updated", patient.id)
        db.commit()
        return serialize(patient)

    @api.get("/patients/{patient_id}/history")
    def histories(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        return [serialize(row) for row in db.scalars(select(ClinicalHistory).where(ClinicalHistory.patient_id == patient_id).order_by(ClinicalHistory.created_at.desc()))]

    @api.get("/patients/{patient_id}/visits")
    def visits(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        return [serialize(row) for row in db.scalars(select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.created_at.desc()))]

    @api.post("/patients/{patient_id}/visits", status_code=201)
    def add_visit(patient_id: str, data: s.VisitCreate, user=Depends(doctor), db=Depends(get_db)):
        patient = owned_patient(db, patient_id, user)
        visit = Visit(patient_id=patient_id, **data.model_dump(mode="json"))
        db.add(visit)
        patient.follow_up_date, patient.updated_at = data.model_dump(mode="json")["follow_up_date"], now()
        audit(db, user, "visit.created", patient_id)
        db.commit()
        return serialize(visit)

    @api.get("/patients/{patient_id}/images")
    def images(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        return [{**serialize(row, ["storage_key"]), "url": f"/api/images/{row.id}/content"} for row in db.scalars(select(MedicalImage).where(MedicalImage.patient_id == patient_id).order_by(MedicalImage.created_at.desc()))]

    @api.post("/patients/{patient_id}/images", status_code=201)
    def upload_image(patient_id: str, request: Request, image: UploadFile = File(...), user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        content, width, height, sha = validate_image(image)
        key = uid() + ".png"
        path = protected_path(request.app.state.storage, key)
        path.write_bytes(content)
        row = MedicalImage(patient_id=patient_id, storage_key=key, sha256=sha, width=width, height=height)
        db.add(row)
        audit(db, user, "image.uploaded", patient_id)
        try:
            db.commit()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {**serialize(row, ["storage_key"]), "url": f"/api/images/{row.id}/content"}

    @api.get("/images/{image_id}/content")
    def image_content(image_id: str, request: Request, user=Depends(doctor), db=Depends(get_db)):
        row = db.get(MedicalImage, image_id)
        if not row:
            raise HTTPException(404, "Image not found")
        owned_patient(db, row.patient_id, user)
        audit(db, user, "image.viewed", row.id)
        db.commit()
        return FileResponse(protected_path(request.app.state.storage, row.storage_key), media_type="image/png")

    @api.post("/patients/{patient_id}/analyze", status_code=201)
    def analyze(patient_id: str, data: s.Analyze, request: Request, user=Depends(doctor), db=Depends(get_db)):
        from ml.inference.image_predictor import ImagePredictor
        owned_patient(db, patient_id, user)
        image = db.get(MedicalImage, data.image_id)
        if not image or image.patient_id != patient_id:
            raise HTTPException(404, "Image not found for this patient")
        heatmap = uid() + ".png"
        destination = protected_path(request.app.state.storage, heatmap)
        try:
            result = ImagePredictor(request.app.state.checkpoint).predict(protected_path(request.app.state.storage, image.storage_key), destination)
        except Exception as error:
            import logging
            logging.getLogger(__name__).exception("ResNet18 analysis failed")
            destination.unlink(missing_ok=True)
            audit(db, user, "analysis.failed", patient_id)
            db.commit()
            raise HTTPException(503, "ResNet18 checkpoint or inference unavailable. Administrator must inspect model validation logs; no prediction was produced.") from error
        row = Analysis(patient_id=patient_id, image_id=image.id, result=result, heatmap_key=heatmap)
        db.add(row)
        audit(db, user, "analysis.created", patient_id)
        db.commit()
        return analysis_json(row)

    @api.get("/patients/{patient_id}/analyses")
    def analyses(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        return [analysis_json(row) for row in db.scalars(select(Analysis).where(Analysis.patient_id == patient_id).order_by(Analysis.created_at.desc()))]

    @api.get("/analyses/{analysis_id}")
    def analysis_detail(analysis_id: str, user=Depends(doctor), db=Depends(get_db)):
        return analysis_json(owned_analysis(db, analysis_id, user))

    @api.patch("/analyses/{analysis_id}")
    def review_analysis(analysis_id: str, data: s.Review, user=Depends(doctor), db=Depends(get_db)):
        row = owned_analysis(db, analysis_id, user)
        row.observations, row.follow_up = data.observations, data.follow_up
        audit(db, user, "analysis.reviewed", row.id)
        db.commit()
        return analysis_json(row)

    @api.get("/analyses/{analysis_id}/heatmap")
    def heatmap_content(analysis_id: str, request: Request, user=Depends(doctor), db=Depends(get_db)):
        row = owned_analysis(db, analysis_id, user)
        audit(db, user, "heatmap.viewed", row.id)
        db.commit()
        return FileResponse(protected_path(request.app.state.storage, row.heatmap_key), media_type="image/png")

    @api.post("/patients/{patient_id}/reports", status_code=201)
    def add_report(patient_id: str, data: s.ReportCreate, request: Request, user=Depends(doctor), db=Depends(get_db)):
        from backend.reports import generate_report
        patient = owned_patient(db, patient_id, user)
        analysis = owned_analysis(db, data.analysis_id, user)
        if analysis.patient_id != patient_id:
            raise HTTPException(404, "Analysis not found for this patient")
        image = db.get(MedicalImage, analysis.image_id)
        key = uid() + ".pdf"
        generate_report(protected_path(request.app.state.storage, key), patient, user, analysis, image, request.app.state.storage)
        row = Report(patient_id=patient_id, analysis_id=analysis.id, storage_key=key)
        db.add(row)
        audit(db, user, "report.created", patient_id)
        db.commit()
        return {**serialize(row, ["storage_key"]), "download_url": f"/api/reports/{row.id}/download"}

    @api.get("/patients/{patient_id}/reports")
    def reports(patient_id: str, user=Depends(doctor), db=Depends(get_db)):
        owned_patient(db, patient_id, user)
        return [{**serialize(row, ["storage_key"]), "download_url": f"/api/reports/{row.id}/download"} for row in db.scalars(select(Report).where(Report.patient_id == patient_id).order_by(Report.created_at.desc()))]

    @api.get("/reports/{report_id}/download")
    def download_report(report_id: str, request: Request, user=Depends(doctor), db=Depends(get_db)):
        row = db.get(Report, report_id)
        if not row:
            raise HTTPException(404, "Report not found")
        owned_patient(db, row.patient_id, user)
        audit(db, user, "report.downloaded", row.id)
        db.commit()
        return FileResponse(protected_path(request.app.state.storage, row.storage_key), media_type="application/pdf", filename=f"research-report-{row.id[:8]}.pdf")

    @api.get("/model/evaluation")
    def model_evaluation(request: Request, user=Depends(current_user)):
        from ml.evaluation_evidence import read_selected_evaluation
        return read_selected_evaluation(request.app.state.checkpoint)

    @api.get("/dashboard")
    def dashboard(user=Depends(current_user), db=Depends(get_db)):
        if user.role == "Admin":
            return {"doctors": db.scalar(select(func.count()).select_from(User).where(User.role == "Doctor")),
                    "active_doctors": db.scalar(select(func.count()).select_from(User).where(User.role == "Doctor", User.active.is_(True))),
                    "patients": db.scalar(select(func.count()).select_from(Patient)),
                    "experiments": db.scalar(select(func.count()).select_from(Experiment)),
                    "analyses": db.scalar(select(func.count()).select_from(Analysis))}
        own = select(Patient.id).where(Patient.doctor_id == user.id)
        return {"patients": db.scalar(select(func.count()).select_from(Patient).where(Patient.doctor_id == user.id)),
                "analyses": db.scalar(select(func.count()).select_from(Analysis).where(Analysis.patient_id.in_(own))),
                "reports": db.scalar(select(func.count()).select_from(Report).where(Report.patient_id.in_(own))),
                "follow_ups": db.scalar(select(func.count()).select_from(Patient).where(Patient.doctor_id == user.id, Patient.follow_up_date.is_not(None), Patient.follow_up_date <= date.today().isoformat()))}

    @api.get("/analyses")
    def all_analyses(user=Depends(doctor), db=Depends(get_db)):
        rows = db.scalars(select(Analysis).join(Patient, Analysis.patient_id == Patient.id).where(Patient.doctor_id == user.id).order_by(Analysis.created_at.desc()).limit(100))
        return [analysis_json(row) for row in rows]

    @api.get("/reports")
    def all_reports(user=Depends(doctor), db=Depends(get_db)):
        rows = db.scalars(select(Report).join(Patient, Report.patient_id == Patient.id).where(Patient.doctor_id == user.id).order_by(Report.created_at.desc()).limit(100))
        return [{**serialize(row, ["storage_key"]), "download_url": f"/api/reports/{row.id}/download"} for row in rows]

    @api.get("/admin/federated/clients")
    def clients(user=Depends(admin), db=Depends(get_db)):
        return [serialize(row) for row in db.scalars(select(FederatedClient).order_by(FederatedClient.id))]

    @api.post("/admin/federated/experiments", status_code=201)
    def add_experiment(data: s.ExperimentConfig, user=Depends(admin), db=Depends(get_db)):
        if data.secure_aggregation:
            from ml.privacy import secure_capability
            capability = secure_capability()
            if not capability["enabled"]:
                raise HTTPException(422, capability["reason"])
        if data.dp.enabled:
            from ml.privacy import capabilities
            if capabilities()["differential_privacy"]["status"] == "dependency_missing":
                raise HTTPException(422, "Opacus is not installed")
        if not (ROOT / "ml/data/manifest.json").is_file():
            raise HTTPException(422, "Run python -m ml.dataset before training")
        with _experiment_lock:
            if db.scalar(select(Experiment).where(Experiment.status.in_(["queued", "running"]))):
                raise HTTPException(409, "Another experiment is queued or running")
            config = {**data.model_dump(), "manifest": str(ROOT / "ml/data/manifest.json"), "threads": 4}
            row = Experiment(algorithm=data.algorithm, config=config)
            db.add(row)
            audit(db, user, "experiment.queued")
            db.commit()
        return serialize(row)

    @api.get("/admin/federated/experiments")
    def experiments(user=Depends(admin), db=Depends(get_db)):
        return [serialize(row) for row in db.scalars(select(Experiment).order_by(Experiment.created_at.desc()).limit(100))]

    @api.get("/admin/federated/experiments/{experiment_id}")
    def experiment(experiment_id: str, user=Depends(admin), db=Depends(get_db)):
        row = db.get(Experiment, experiment_id)
        if not row:
            raise HTTPException(404, "Experiment not found")
        return serialize(row)

    @api.get("/admin/federated/experiments/{experiment_id}/rounds")
    def experiment_rounds(experiment_id: str, user=Depends(admin), db=Depends(get_db)):
        if not db.get(Experiment, experiment_id):
            raise HTTPException(404, "Experiment not found")
        return [serialize(row) for row in db.scalars(select(RoundMetric).where(RoundMetric.experiment_id == experiment_id).order_by(RoundMetric.round_number))]

    @api.get("/admin/federated/comparison")
    def comparison(user=Depends(admin), db=Depends(get_db)):
        return [{"id": row.id, "algorithm": row.algorithm, "config": row.config, "results": row.results} for row in db.scalars(select(Experiment).where(Experiment.status == "completed").order_by(Experiment.created_at.desc()))]

    @api.get("/admin/federated/privacy")
    def privacy(user=Depends(admin), db=Depends(get_db)):
        from ml.privacy import capabilities
        secure_rounds = []
        for row in db.scalars(select(RoundMetric).join(Experiment).where(Experiment.status == "completed").order_by(RoundMetric.id.desc()).limit(300)):
            evidence = row.metrics.get("secure_aggregation")
            if isinstance(evidence, dict) and evidence.get("status") == "completed":
                secure_rounds.append({"experiment_id": row.experiment_id, "round_number": row.round_number, "evidence": evidence})
        return {"capabilities": capabilities(), "secure_rounds": secure_rounds,
                "metrics": [serialize(row) for row in db.scalars(select(PrivacyMetric).join(Experiment).where(Experiment.status == "completed").order_by(PrivacyMetric.id.desc()).limit(300))]}

    @api.get("/admin/audit")
    def audit_logs(page: int = Query(1, ge=1), user=Depends(admin), db=Depends(get_db)):
        # Patient resource identifiers are redacted from the admin audit view.
        rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * 50).limit(50))
        return [{**serialize(row), "resource": row.resource if row.action.startswith(("doctor.", "experiment.", "auth.")) else "protected"} for row in rows]

    @api.get("/admin/system")
    def system(request: Request, user=Depends(admin), db=Depends(get_db)):
        from ml.checkpoints import load_checkpoint, file_sha256
        from ml.privacy import capabilities
        try:
            _, metadata, _ = load_checkpoint(request.app.state.checkpoint)
            model = {"status": "validated", "metadata": metadata, "sha256": file_sha256(request.app.state.checkpoint)}
        except Exception as error:
            model = {"status": "unavailable", "error": str(error)}
        return {"model": model, "database": "connected", "privacy": capabilities(), "roles": ["Admin", "Doctor"],
                "worker": "Run python -m backend.worker in a separate process", "research_only": True,
                "settings": {"cookie_secure": os.environ.get("COOKIE_SECURE", "false"), "upload_max_mib": 10}}

    app.include_router(api)
    return app


def update_doctor(db, account, data):
    values = data.model_dump(exclude_unset=True)
    if "name" in values:
        account.name = values.pop("name")
    if "password" in values:
        account.password_hash = password_hash(values.pop("password"))
        for session in db.scalars(select(Session).where(Session.user_id == account.id)):
            db.delete(session)
    profile = db.get(DoctorProfile, account.id)
    if not profile:
        profile = DoctorProfile(user_id=account.id)
        db.add(profile)
    for key, value in values.items():
        setattr(profile, key, value or "")


app = create_app()

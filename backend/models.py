from datetime import datetime, timezone
import uuid

from sqlalchemy import JSON, Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.database import Base


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('Admin', 'Doctor')"),)
    id = Column(String, primary_key=True, default=uid)
    email = Column(String(254), unique=True, nullable=False)
    name = Column(String(160), nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String(10), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(String, default=now, nullable=False)


class SetupState(Base):
    __tablename__ = "setup_state"
    id = Column(String, primary_key=True)
    completed_at = Column(String, default=now, nullable=False)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    specialty = Column(String(160), default="")
    hospital = Column(String(160), default="")
    registration = Column(String(160), default="")


class Session(Base):
    __tablename__ = "sessions"
    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    csrf_token = Column(String, nullable=False)
    expires_at = Column(Float, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key = Column(String, primary_key=True)
    count = Column(Integer, default=0, nullable=False)
    window_start = Column(Float, nullable=False)


class Patient(Base):
    __tablename__ = "patients"
    id = Column(String, primary_key=True, default=lambda: "PT-" + uid()[:12].upper())
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    full_name = Column(String(160), nullable=False, index=True)
    date_of_birth = Column(String(10), nullable=False)
    sex = Column(String(30), nullable=False)
    contact = Column(String(200), default="")
    smoking_status = Column(String(30), default="Unknown")
    smoking_history = Column(Text, default="")
    family_history = Column(Text, default="")
    respiratory_conditions = Column(Text, default="")
    symptoms = Column(Text, default="")
    medical_history = Column(Text, default="")
    allergies = Column(Text, default="")
    medications = Column(Text, default="")
    doctor_notes = Column(Text, default="")
    follow_up_date = Column(String(10), nullable=True)
    created_at = Column(String, default=now, nullable=False)
    updated_at = Column(String, default=now, nullable=False)


class ClinicalHistory(Base):
    __tablename__ = "clinical_histories"
    id = Column(String, primary_key=True, default=uid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    snapshot = Column(JSON, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Visit(Base):
    __tablename__ = "visits"
    id = Column(String, primary_key=True, default=uid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    notes = Column(Text, nullable=False)
    follow_up_date = Column(String, nullable=True)
    created_at = Column(String, default=now, nullable=False)


class MedicalImage(Base):
    __tablename__ = "medical_images"
    id = Column(String, primary_key=True, default=uid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    storage_key = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(String, primary_key=True, default=uid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    image_id = Column(String, ForeignKey("medical_images.id"), nullable=False)
    result = Column(JSON, nullable=False)
    heatmap_key = Column(String, nullable=False)
    observations = Column(Text, default="")
    follow_up = Column(Text, default="")
    created_at = Column(String, default=now, nullable=False)


class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=uid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    storage_key = Column(String, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class FederatedClient(Base):
    __tablename__ = "federated_clients"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="simulation-ready")


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String, primary_key=True, default=uid)
    algorithm = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="queued")
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(String, default=now, nullable=False)
    completed_at = Column(String, nullable=True)


class RoundMetric(Base):
    __tablename__ = "round_metrics"
    __table_args__ = (UniqueConstraint("experiment_id", "round_number"),)
    id = Column(String, primary_key=True, default=uid)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=False)


class PrivacyMetric(Base):
    __tablename__ = "privacy_metrics"
    id = Column(String, primary_key=True, default=uid)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    client = Column(String, nullable=False)
    metrics = Column(JSON, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=uid)
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    created_at = Column(String, default=now, nullable=False)

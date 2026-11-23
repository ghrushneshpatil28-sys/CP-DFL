from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Password = Annotated[str, StringConstraints(strip_whitespace=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: Password = Field(min_length=1, max_length=128)


class AdminSetup(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: Password = Field(min_length=12, max_length=128)
    setup_token: str = Field(min_length=32, max_length=128)


class DoctorCreate(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: Password = Field(min_length=12, max_length=128)
    specialty: str = Field(default="", max_length=160)
    hospital: str = Field(default="", max_length=160)
    registration: str = Field(default="", max_length=160)


class DoctorUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    specialty: str | None = Field(default=None, max_length=160)
    hospital: str | None = Field(default=None, max_length=160)
    registration: str | None = Field(default=None, max_length=160)
    password: Password | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("name", "password")
    @classmethod
    def no_explicit_null(cls, value):
        if value is None:
            raise ValueError("Omit this field rather than null")
        return value


class AccountStatus(StrictModel):
    active: bool


class PatientData(StrictModel):
    full_name: str = Field(min_length=2, max_length=160)
    date_of_birth: date
    sex: Literal["Female", "Male", "Other", "Not specified"]
    contact: str = Field(default="", max_length=200)
    smoking_status: Literal["Never", "Former", "Current", "Unknown"] = "Unknown"
    smoking_history: str = Field(default="", max_length=4000)
    family_history: str = Field(default="", max_length=4000)
    respiratory_conditions: str = Field(default="", max_length=4000)
    symptoms: str = Field(default="", max_length=4000)
    medical_history: str = Field(default="", max_length=8000)
    allergies: str = Field(default="", max_length=4000)
    medications: str = Field(default="", max_length=4000)
    doctor_notes: str = Field(default="", max_length=8000)
    follow_up_date: date | None = None

    @field_validator("date_of_birth")
    @classmethod
    def valid_birth(cls, value):
        if value > date.today() or value.year < 1900:
            raise ValueError("Birth date must be between 1900 and today")
        return value


class PatientPatch(StrictModel):
    # Validated against PatientData after merging with the persisted record.
    full_name: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    contact: str | None = None
    smoking_status: str | None = None
    smoking_history: str | None = None
    family_history: str | None = None
    respiratory_conditions: str | None = None
    symptoms: str | None = None
    medical_history: str | None = None
    allergies: str | None = None
    medications: str | None = None
    doctor_notes: str | None = None
    follow_up_date: date | None = None


class VisitCreate(StrictModel):
    notes: str = Field(min_length=1, max_length=8000)
    follow_up_date: date | None = None


class Analyze(StrictModel):
    image_id: str


class Review(StrictModel):
    observations: str = Field(default="", max_length=8000)
    follow_up: str = Field(default="", max_length=8000)


class ReportCreate(StrictModel):
    analysis_id: str


# Re-export the shared training contract for existing API annotations.
from ml.config import DPConfig, ExperimentConfig

"""Pydantic request/response schemas (the public API contract)."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["scheduled", "checked_in", "completed", "cancelled", "no_show"]
VisitType = Literal["consultation", "follow_up", "emergency", "lab_review", "vaccination"]


def _ensure_utc(value: datetime | None) -> datetime | None:
    """Treat naive datetimes as UTC so comparisons are always timezone-aware."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class DoctorBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=120, examples=["Dr. Meera Iyer"])
    specialty: str = Field(min_length=2, max_length=80, examples=["Cardiology"])
    room: str = Field(min_length=1, max_length=20, examples=["B-204"])


class DoctorCreate(DoctorBase):
    """Payload for registering a doctor."""


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AppointmentBase(BaseModel):
    patient_name: str = Field(min_length=2, max_length=120, examples=["Rahul Verma"])
    patient_phone: str = Field(pattern=r"^\+?[0-9 \-]{7,20}$", examples=["+91 98765 43210"])
    doctor_id: int = Field(gt=0)
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=240)
    visit_type: VisitType = "consultation"
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("scheduled_at")
    @classmethod
    def _normalise_tz(cls, value: datetime) -> datetime:
        return _ensure_utc(value)


class AppointmentCreate(AppointmentBase):
    """Payload for booking a new appointment."""


class AppointmentUpdate(BaseModel):
    """Partial update; only supplied fields are changed."""

    patient_name: str | None = Field(default=None, min_length=2, max_length=120)
    patient_phone: str | None = Field(default=None, pattern=r"^\+?[0-9 \-]{7,20}$")
    doctor_id: int | None = Field(default=None, gt=0)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=10, le=240)
    visit_type: VisitType | None = None
    status: Status | None = None
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("scheduled_at")
    @classmethod
    def _normalise_tz(cls, value: datetime | None) -> datetime | None:
        return _ensure_utc(value)


class AppointmentRead(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: Status
    doctor: DoctorRead
    created_at: datetime
    updated_at: datetime


class DoctorLoad(BaseModel):
    doctor_id: int
    full_name: str
    specialty: str
    active_appointments: int


class AppointmentStats(BaseModel):
    """Aggregates that drive the dashboard KPI cards."""

    total: int
    today: int
    upcoming: int
    by_status: dict[str, int]
    completion_rate: float
    doctor_load: list[DoctorLoad]

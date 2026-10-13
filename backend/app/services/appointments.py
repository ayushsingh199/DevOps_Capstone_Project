"""Appointment business logic: booking, double-booking prevention and dashboard stats."""

import logging
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.metrics import APPOINTMENT_STATUS_CHANGES, APPOINTMENTS_BOOKED, BOOKING_CONFLICTS
from app.models import APPOINTMENT_STATUSES, Appointment, Doctor
from app.schemas import AppointmentCreate, AppointmentStats, AppointmentUpdate, DoctorLoad
from app.services.doctors import get_doctor

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("scheduled", "checked_in")
MAX_DURATION = timedelta(minutes=240)


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; Postgres returns aware ones. Normalise both to UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


def list_appointments(
    db: Session,
    status: str | None = None,
    doctor_id: int | None = None,
    on_date: date | None = None,
    search: str | None = None,
) -> list[Appointment]:
    """Return appointments matching the optional filters, soonest first."""
    query = select(Appointment).order_by(Appointment.scheduled_at)
    if status:
        query = query.where(Appointment.status == status)
    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)
    if on_date:
        start, end = _day_bounds(on_date)
        query = query.where(Appointment.scheduled_at >= start, Appointment.scheduled_at < end)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(Appointment.patient_name.ilike(pattern), Appointment.reason.ilike(pattern))
        )
    return list(db.scalars(query).unique())


def get_appointment(db: Session, appointment_id: int) -> Appointment:
    """Return one appointment or raise NotFoundError."""
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    return appointment


def _assert_slot_free(
    db: Session,
    doctor_id: int,
    start: datetime,
    duration_minutes: int,
    exclude_id: int | None = None,
) -> None:
    """Raise ConflictError if the doctor already has an active booking overlapping the slot."""
    start = _as_utc(start)
    end = start + timedelta(minutes=duration_minutes)
    query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.scheduled_at > start - MAX_DURATION,
        Appointment.scheduled_at < end,
    )
    if exclude_id is not None:
        query = query.where(Appointment.id != exclude_id)
    for existing in db.scalars(query).unique():
        existing_start = _as_utc(existing.scheduled_at)
        existing_end = existing_start + timedelta(minutes=existing.duration_minutes)
        if existing_start < end and existing_end > start:
            BOOKING_CONFLICTS.inc()
            logger.warning(
                "double booking rejected",
                extra={"doctor_id": doctor_id, "clashes_with": existing.id},
            )
            raise ConflictError(
                f"Doctor {doctor_id} is already booked at "
                f"{existing_start:%Y-%m-%d %H:%M} UTC (appointment #{existing.id})"
            )


def create_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
    """Book an appointment after validating the doctor and the time slot."""
    get_doctor(db, payload.doctor_id)
    _assert_slot_free(db, payload.doctor_id, payload.scheduled_at, payload.duration_minutes)
    appointment = Appointment(**payload.model_dump(), status="scheduled")
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    APPOINTMENTS_BOOKED.labels(visit_type=appointment.visit_type).inc()
    logger.info("appointment booked", extra={"appointment_id": appointment.id})
    return appointment


def update_appointment(db: Session, appointment_id: int, payload: AppointmentUpdate) -> Appointment:
    """Apply a partial update, re-checking the slot if the timing or doctor changed."""
    appointment = get_appointment(db, appointment_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "doctor_id" in changes:
        get_doctor(db, changes["doctor_id"])

    new_status = changes.get("status", appointment.status)
    timing_changed = bool({"doctor_id", "scheduled_at", "duration_minutes"} & changes.keys())
    reactivated = new_status in ACTIVE_STATUSES and appointment.status not in ACTIVE_STATUSES
    if new_status in ACTIVE_STATUSES and (timing_changed or reactivated):
        _assert_slot_free(
            db,
            changes.get("doctor_id", appointment.doctor_id),
            changes.get("scheduled_at", appointment.scheduled_at),
            changes.get("duration_minutes", appointment.duration_minutes),
            exclude_id=appointment.id,
        )

    previous_status = appointment.status
    for field, value in changes.items():
        setattr(appointment, field, value)
    db.commit()
    db.refresh(appointment)
    if appointment.status != previous_status:
        APPOINTMENT_STATUS_CHANGES.labels(status=appointment.status).inc()
    logger.info(
        "appointment updated",
        extra={"appointment_id": appointment.id, "fields": sorted(changes)},
    )
    return appointment


def delete_appointment(db: Session, appointment_id: int) -> None:
    """Permanently remove an appointment."""
    appointment = get_appointment(db, appointment_id)
    db.delete(appointment)
    db.commit()
    logger.info("appointment deleted", extra={"appointment_id": appointment_id})


def appointment_stats(db: Session, now: datetime | None = None) -> AppointmentStats:
    """Compute the KPI aggregates shown on the dashboard."""
    now = now or datetime.now(UTC)
    start, end = _day_bounds(now.date())

    rows = db.execute(select(Appointment.status, func.count()).group_by(Appointment.status)).all()
    by_status = dict.fromkeys(APPOINTMENT_STATUSES, 0) | {row[0]: row[1] for row in rows}
    total = sum(by_status.values())

    today = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.scheduled_at >= start, Appointment.scheduled_at < end)
    )
    upcoming = db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.scheduled_at >= now, Appointment.status == "scheduled")
    )
    closed = by_status["completed"] + by_status["no_show"]
    completion_rate = round(by_status["completed"] / closed * 100, 1) if closed else 0.0

    load_rows = db.execute(
        select(Doctor.id, Doctor.full_name, Doctor.specialty, func.count(Appointment.id))
        .outerjoin(
            Appointment,
            (Appointment.doctor_id == Doctor.id) & Appointment.status.in_(ACTIVE_STATUSES),
        )
        .group_by(Doctor.id, Doctor.full_name, Doctor.specialty)
        .order_by(func.count(Appointment.id).desc(), Doctor.full_name)
    ).all()
    doctor_load = [
        DoctorLoad(doctor_id=r[0], full_name=r[1], specialty=r[2], active_appointments=r[3])
        for r in load_rows
    ]
    return AppointmentStats(
        total=total,
        today=today or 0,
        upcoming=upcoming or 0,
        by_status=by_status,
        completion_rate=completion_rate,
        doctor_load=doctor_load,
    )

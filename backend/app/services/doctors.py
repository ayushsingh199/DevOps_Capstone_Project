"""Doctor business logic."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Appointment, Doctor
from app.schemas import DoctorCreate

logger = logging.getLogger(__name__)


def list_doctors(db: Session) -> list[Doctor]:
    """Return all doctors ordered by name."""
    return list(db.scalars(select(Doctor).order_by(Doctor.full_name)))


def get_doctor(db: Session, doctor_id: int) -> Doctor:
    """Return one doctor or raise NotFoundError."""
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise NotFoundError(f"Doctor {doctor_id} not found")
    return doctor


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    """Register a new doctor."""
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    logger.info("doctor created", extra={"doctor_id": doctor.id})
    return doctor


def delete_doctor(db: Session, doctor_id: int) -> None:
    """Delete a doctor that has no appointments on record."""
    doctor = get_doctor(db, doctor_id)
    booked = db.scalar(
        select(func.count()).select_from(Appointment).where(Appointment.doctor_id == doctor_id)
    )
    if booked:
        raise ConflictError(f"Doctor {doctor_id} has {booked} appointment(s) and cannot be removed")
    db.delete(doctor)
    db.commit()
    logger.info("doctor deleted", extra={"doctor_id": doctor_id})

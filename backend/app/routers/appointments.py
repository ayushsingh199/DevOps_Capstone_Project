"""REST endpoints for appointments."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStats,
    AppointmentUpdate,
    Status,
)
from app.services import appointments as service

router = APIRouter(prefix="/api/appointments", tags=["appointments"])
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: DB,
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    doctor_id: int | None = None,
    on_date: Annotated[date | None, Query(alias="date")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    """List appointments, optionally filtered by status, doctor, day or free-text search."""
    return service.list_appointments(db, status_filter, doctor_id, on_date, q)


@router.get("/stats", response_model=AppointmentStats)
def appointment_stats(db: DB):
    """Dashboard KPIs: totals, today's load, status breakdown and per-doctor load."""
    return service.appointment_stats(db)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: DB):
    """Fetch a single appointment."""
    return service.get_appointment(db, appointment_id)


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, db: DB):
    """Book an appointment. Returns 409 if the doctor is already booked for that slot."""
    return service.create_appointment(db, payload)


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: DB):
    """Reschedule, reassign or change the status of an appointment."""
    return service.update_appointment(db, appointment_id, payload)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: int, db: DB) -> Response:
    """Delete an appointment."""
    service.delete_appointment(db, appointment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

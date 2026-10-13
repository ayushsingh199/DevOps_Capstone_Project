"""REST endpoints for doctors."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DoctorCreate, DoctorRead
from app.services import doctors as service

router = APIRouter(prefix="/api/doctors", tags=["doctors"])
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[DoctorRead])
def list_doctors(db: DB):
    """List all doctors."""
    return service.list_doctors(db)


@router.get("/{doctor_id}", response_model=DoctorRead)
def get_doctor(doctor_id: int, db: DB):
    """Fetch a single doctor."""
    return service.get_doctor(db, doctor_id)


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: DB):
    """Register a doctor."""
    return service.create_doctor(db, payload)


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(doctor_id: int, db: DB) -> Response:
    """Remove a doctor with no appointment history (409 otherwise)."""
    service.delete_doctor(db, doctor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

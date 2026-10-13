"""Optional demo data so a fresh environment shows a populated dashboard.

Run with `python -m app.seed`. It is a no-op when appointments already exist.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.logging_config import configure_logging
from app.models import Appointment, Doctor

logger = logging.getLogger(__name__)

PATIENTS = [
    ("Aarav Sharma", "+91 98100 11223", "consultation", "Persistent chest discomfort"),
    ("Diya Patel", "+91 98200 44556", "follow_up", "Post-operative review"),
    ("Kabir Singh", "+91 98300 77889", "lab_review", "Lipid profile results"),
    ("Ananya Rao", "+91 98400 99001", "vaccination", "Influenza booster"),
    ("Vihaan Gupta", "+91 98500 22334", "emergency", "Sprained ankle"),
    ("Isha Nair", "+91 98600 55667", "consultation", "Recurring migraines"),
    ("Arjun Mehta", "+91 98700 88990", "follow_up", "Blood pressure check"),
    ("Saanvi Joshi", "+91 98800 12121", "consultation", "Skin rash"),
]
# (day offset, hour, status) — a mix of past, today and future visits.
SCHEDULE = [
    (-2, 10, "completed"),
    (-1, 11, "completed"),
    (-1, 15, "no_show"),
    (0, 9, "checked_in"),
    (0, 12, "scheduled"),
    (1, 10, "scheduled"),
    (2, 14, "scheduled"),
    (3, 16, "cancelled"),
]


def seed() -> int:
    """Insert demo appointments if the table is empty. Returns how many rows were added."""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Appointment)):
            logger.info("seed skipped: appointments already present")
            return 0
        doctors = list(db.scalars(select(Doctor).order_by(Doctor.id)))
        if not doctors:
            logger.warning("seed skipped: no doctors found, run migrations first")
            return 0
        midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        for i, ((name, phone, visit, reason), (offset, hour, status)) in enumerate(
            zip(PATIENTS, SCHEDULE, strict=True)
        ):
            db.add(
                Appointment(
                    patient_name=name,
                    patient_phone=phone,
                    doctor_id=doctors[i % len(doctors)].id,
                    scheduled_at=midnight + timedelta(days=offset, hours=hour),
                    duration_minutes=30,
                    visit_type=visit,
                    status=status,
                    reason=reason,
                )
            )
        db.commit()
        logger.info("seeded demo appointments", extra={"count": len(PATIENTS)})
        return len(PATIENTS)


if __name__ == "__main__":
    configure_logging()
    seed()

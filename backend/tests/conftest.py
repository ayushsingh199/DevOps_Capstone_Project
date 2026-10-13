"""Shared fixtures.

Tests never touch the production PostgreSQL database: every test gets a brand-new
in-memory SQLite database, wired in through FastAPI's dependency override.
"""

import os

# Must be set before `app` is imported so the module-level engine never points at Postgres.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["APP_VERSION"] = "test-sha"

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Doctor


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    session.add_all(
        [
            Doctor(full_name="Dr. Test Heart", specialty="Cardiology", room="T-1"),
            Doctor(full_name="Dr. Test Bone", specialty="Orthopaedics", room="T-2"),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def tomorrow_10am() -> datetime:
    day = datetime.now(UTC) + timedelta(days=1)
    return day.replace(hour=10, minute=0, second=0, microsecond=0)


@pytest.fixture()
def booking(tomorrow_10am: datetime) -> dict:
    """A valid appointment payload for doctor #1."""
    return {
        "patient_name": "Rahul Verma",
        "patient_phone": "+91 98765 43210",
        "doctor_id": 1,
        "scheduled_at": tomorrow_10am.isoformat(),
        "duration_minutes": 30,
        "visit_type": "consultation",
        "reason": "Annual check-up",
    }

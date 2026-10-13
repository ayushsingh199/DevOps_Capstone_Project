"""Liveness, readiness and build-info endpoints used by Kubernetes and the UI."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/")
def root() -> dict[str, str]:
    """Service banner."""
    settings = get_settings()
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: the process is up. Deliberately does not touch the database."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    """Readiness probe: only report READY when the database answers."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("readiness check failed: database unreachable")
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "down"})
    return JSONResponse(content={"status": "ready", "database": "up"})


@router.get("/api/info")
def info() -> dict[str, str]:
    """Build metadata shown in the UI footer, so a deploy is visibly traceable to a commit."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }

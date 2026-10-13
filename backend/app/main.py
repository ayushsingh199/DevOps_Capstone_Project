"""FastAPI application factory and process-wide wiring."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.exceptions import DomainError
from app.logging_config import configure_logging
from app.routers import appointments, doctors, health

QUIET_PATHS = {"/health", "/ready", "/metrics"}
logger = logging.getLogger("medislot.http")


def create_app() -> FastAPI:
    """Build the FastAPI app with routers, middleware, error handling and metrics."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Clinic appointment scheduling API for the MediSlot platform.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        if request.url.path not in QUIET_PATHS:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health.router)
    app.include_router(doctors.router)
    app.include_router(appointments.router)

    Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
        app, include_in_schema=False
    )
    logger.info("application started", extra={"version": settings.app_version})
    return app


app = create_app()

# syntax=docker/dockerfile:1.7
# ---------- Stage 1: build wheels (compilers & caches never reach the runtime image) ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- Stage 2: minimal runtime ----------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="medislot-backend" \
      org.opencontainers.image.description="MediSlot clinic appointment API (FastAPI)" \
      org.opencontainers.image.source="https://github.com/ayushsingh199/DevOps_Capstone_Project"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Patch OS packages, then create an unprivileged user with a fixed UID (matches k8s runAsUser).
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels \
    && pip uninstall -y pip setuptools wheel 2>/dev/null || true

COPY --chown=app:app alembic.ini start.sh ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["./start.sh"]

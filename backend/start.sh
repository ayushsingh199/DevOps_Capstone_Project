#!/bin/sh
# Container entrypoint for Docker Compose: migrate, optionally seed, then serve.
# In Kubernetes migrations run in an initContainer and only uvicorn is started.
set -eu

echo "Applying database migrations..."
alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'

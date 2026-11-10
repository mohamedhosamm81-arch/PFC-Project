#!/bin/sh
# Production entrypoint: wait for MySQL, apply migrations, seed, then serve.
set -eu

cd /app

echo "[entrypoint] Waiting for MySQL..."
python -m app.db.wait_for_db

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-true}" = "true" ]; then
    echo "[entrypoint] Seeding reference and admin data..."
    if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
        python -m app.db.seed --demo
    else
        python -m app.db.seed
    fi
fi

echo "[entrypoint] Starting PFC API on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}" \
    --no-access-log

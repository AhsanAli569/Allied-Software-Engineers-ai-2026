#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting ASE AI backend..."
# Render (and some other PaaS hosts) inject $PORT and require the app to listen on it;
# docker-compose.prod.yml doesn't set it, so this still defaults to 8000 there.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${UVICORN_WORKERS:-4}"

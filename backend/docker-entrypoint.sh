#!/bin/sh

if [ "$1" = "api" ]; then
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

if [ "$1" = "worker" ]; then
    exec celery -A app.workers.celery_app worker --loglevel=info
fi

exec "$@"

#!/bin/sh

if [ "$1" = "api" ]; then
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

if [ "$1" = "worker" ]; then
    exec celery -A app.workers.celery_app worker --loglevel=info
fi

if [ "$1" = "worker-research" ]; then
    exec celery -A app.workers.celery_app worker \
        --queues=research --concurrency=1 --loglevel=info
fi

if [ "$1" = "worker-content" ]; then
    exec celery -A app.workers.celery_app worker \
        --queues=content --concurrency=1 --loglevel=info
fi

exec "$@"

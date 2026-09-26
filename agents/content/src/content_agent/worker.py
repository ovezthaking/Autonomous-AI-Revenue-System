"""Celery entry point: `celery -A content_agent.worker:celery_app worker`."""

from revenue_swarm.celery import celery_app

import content_agent.tasks  # noqa: F401  — registers the task

__all__ = ["celery_app"]

"""Celery entry: `celery -A ebook_agent.worker:celery_app worker`."""

from revenue_swarm.celery import celery_app

import ebook_agent.tasks  # noqa: F401  — registers the tasks

__all__ = ["celery_app"]

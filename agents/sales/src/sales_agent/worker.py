"""Celery entry: `celery -A sales_agent.worker:celery_app worker`."""

from revenue_swarm.celery import celery_app

import sales_agent.tasks  # noqa: F401

__all__ = ["celery_app"]

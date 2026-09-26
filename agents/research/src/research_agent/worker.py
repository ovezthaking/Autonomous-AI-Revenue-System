"""Celery entry point: `celery -A research_agent.worker:celery_app worker`."""

from revenue_swarm.celery import celery_app

import research_agent.tasks  # noqa: F401  — registers the task

__all__ = ["celery_app"]

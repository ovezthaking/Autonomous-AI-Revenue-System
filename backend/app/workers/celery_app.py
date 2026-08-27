from app.core.config import REDIS_URL
from celery import Celery

celery_app = Celery(
    "revenue_swarm",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"],
)
celery_app.conf.task_track_started = True

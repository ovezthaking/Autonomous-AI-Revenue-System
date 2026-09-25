from app.core.config import REDIS_URL
from celery import Celery

celery_app = Celery(
    "revenue_swarm",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks",
        "app.workers.research",
        "app.workers.content",
    ],
)
celery_app.conf.task_track_started = True
celery_app.conf.task_routes = {
    "research.discover_programs": {"queue": "research"},
    "content.generate": {"queue": "content"},
    "content.publish_due": {"queue": "content"},
}
celery_app.conf.beat_schedule = {
    "publish-due-every-5-min": {
        "task": "content.publish_due",
        "schedule": 300.0
    },
}
celery_app.conf.timezone = "UTC"

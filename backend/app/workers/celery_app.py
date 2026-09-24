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

from celery import Celery

from revenue_swarm.config import REDIS_URL
from revenue_swarm.tasks import Queue, TaskName

celery_app = Celery("revenue_swarm", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_track_started = True
celery_app.conf.task_routes = {
    TaskName.RESEARCH_DISCOVER.value: {"queue": Queue.RESEARCH.value},
    TaskName.CONTENT_GENERATE.value: {"queue": Queue.CONTENT.value},
    TaskName.CONTENT_PUBLISH_DUE.value: {"queue": Queue.CONTENT.value},
}
celery_app.conf.beat_schedule = {
    "publish-due-every-5-min": {
        "task": TaskName.CONTENT_PUBLISH_DUE.value,
        "schedule": 300.0,
    },
}
celery_app.conf.timezone = "UTC"

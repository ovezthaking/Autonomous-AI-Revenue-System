from celery import Celery
from celery.schedules import crontab

from revenue_swarm.config import REDIS_URL
from revenue_swarm.tasks import Queue, TaskName

celery_app = Celery("revenue_swarm", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_track_started = True
celery_app.conf.task_routes = {
    TaskName.RESEARCH_DISCOVER.value: {"queue": Queue.RESEARCH.value},
    TaskName.RESEARCH_RESCORE.value: {"queue": Queue.RESEARCH.value},
    TaskName.AFFILIATE_SYNC.value: {"queue": Queue.RESEARCH.value},
    TaskName.AFFILIATE_CHECK_LINKS.value: {"queue": Queue.RESEARCH.value},
    TaskName.AFFILIATE_CHECK_PENDING.value: {"queue": Queue.RESEARCH.value},
    TaskName.CONTENT_GENERATE.value: {"queue": Queue.CONTENT.value},
    TaskName.CONTENT_PUBLISH_DUE.value: {"queue": Queue.CONTENT.value},
    TaskName.CONTENT_RETRACT.value: {"queue": Queue.CONTENT.value},
    TaskName.EBOOK_PROPOSE.value: {"queue": Queue.EBOOK.value},
    TaskName.EBOOK_OUTLINE.value: {"queue": Queue.EBOOK.value},
    TaskName.EBOOK_WRITE.value: {"queue": Queue.EBOOK.value},
    TaskName.EBOOK_ASSEMBLE.value: {"queue": Queue.EBOOK.value},
    TaskName.SALES_FULFILL.value: {"queue": Queue.SALES.value},
    TaskName.SALES_REFUND.value: {"queue": Queue.SALES.value},
}
celery_app.conf.beat_schedule = {
    "publish-due-every-5-min": {
        "task": TaskName.CONTENT_PUBLISH_DUE.value,
        "schedule": 900.0,
    },
    "affiliate-check-links": {
        "task": TaskName.AFFILIATE_CHECK_LINKS.value,
        "schedule": crontab(hour=3, minute=15),
    },
    "affiliate-check-pending": {
        "task": TaskName.AFFILIATE_CHECK_PENDING.value,
        "schedule": crontab(hour=8, minute=0),
    },
}
celery_app.conf["timezone"] = "UTC"

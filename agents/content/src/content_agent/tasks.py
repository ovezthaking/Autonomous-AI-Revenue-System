from datetime import UTC, datetime

from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import ContentStatus
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.tasks import TaskName, run_agent_task
from sqlalchemy import select

from content_agent.agent import generate_content


@celery_app.task(name=TaskName.CONTENT_GENERATE.value)
def generate_content_task(task_id: str) -> None:
    def handler(db, row):
        limit = int(row.input.get("limit", 3))
        return generate_content(db, row.id, limit)

    run_agent_task(task_id, handler)


@celery_app.task(name=TaskName.CONTENT_PUBLISH_DUE.value)
def publish_due_task() -> int:
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        stmt = select(ContentItem).where(
            ContentItem.status == ContentStatus.SCHEDULED.value,
            ContentItem.scheduled_for.is_not(None),
            ContentItem.scheduled_for <= now,
        )
        rows = list(db.scalars(stmt).all())
        for row in rows:
            row.status = ContentStatus.PUBLISHED.value
            row.published_at = now
        db.commit()
        return len(rows)
    finally:
        db.close()

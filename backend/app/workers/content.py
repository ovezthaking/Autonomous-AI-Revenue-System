import uuid
from datetime import UTC, datetime

from app.agents.content.agent import generate_content
from app.core.db import SessionLocal
from app.core.enums import ContentStatus
from app.models.content_item import ContentItem
from app.models.task import AgentTask
from app.workers.celery_app import celery_app
from sqlalchemy import select


@celery_app.task(name="content.generate")
def generate_content_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.now(UTC)
        db.commit()

        limit = int(row.input.get("limit", 3))
        result = generate_content(db, row.id, limit)

        row.output = result
        row.status = "succeeded"
        row.finished_at = datetime.now(UTC)
        row.error = None
        db.commit()
    except Exception as e:
        db.rollback()
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is not None:
            row.status = "failed"
            row.error = str(e)
            row.finished_at = datetime.now(UTC)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="content.publish_due")
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

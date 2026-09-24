from datetime import UTC, datetime

from app.core.db import SessionLocal
from app.core.enums import ContentStatus
from app.models.content_item import ContentItem
from app.workers.celery_app import celery_app
from sqlalchemy.sql import select


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
            row.status = (ContentStatus.PUBLISHED.value,)
            row.published_at = now
        db.commit()
        return len(rows)
    finally:
        db.close()

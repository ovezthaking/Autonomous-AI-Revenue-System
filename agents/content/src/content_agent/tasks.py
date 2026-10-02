from datetime import UTC, datetime

from sqlalchemy.orm import Session

from content_agent.setting import PUBLISH_MAX_ATTEMPTS
from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import ContentStatus, PublicationStatus
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.publication import Publication
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


def reserve(db: Session, item: ContentItem, target: str) -> Publication | None:
    """Claims the delivery slot. None means: do not publish now."""
    existing = db.scalar(
        select(Publication).where(
            Publication.content_item_id == item.id,
            Publication.target == target,
        )
    )
    if existing is None:
        row = Publication(
            content_item_id=item.id,
            target=target,
            status=PublicationStatus.IN_FLIGHT.value,
            attempts=1,
        )
        db.add(row)
        db.commit()
        return row

    if existing.status == PublicationStatus.SUCCEEDED.value:
        return None
    if existing.status == PublicationStatus.IN_FLIGHT.value:
        existing.status = PublicationStatus.NEEDS_REVIEW.value
        existing.error = "Previous attempt did not finish"
        db.commit()
        return None
    if existing.status in (
        PublicationStatus.NEEDS_REVIEW.value,
        PublicationStatus.RETRACTED.value,
    ):
        return None
    if (existing.payload or {}).get("retryable") is False:
        return None
    if existing.attempts >= PUBLISH_MAX_ATTEMPTS:
        existing.status = PublicationStatus.NEEDS_REVIEW.value
        existing.error = "Attempt limit reached"
        db.commit()
        return None
    existing.status = PublicationStatus.IN_FLIGHT.value
    existing.attempts += 1
    existing.error = None
    db.commit()
    return existing

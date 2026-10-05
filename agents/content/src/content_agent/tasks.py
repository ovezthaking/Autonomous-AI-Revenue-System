import uuid
from datetime import UTC, datetime

from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import (
    ContentStatus,
    HitlDecisionValue,
    HitlEntityType,
    PublicationStatus,
)
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.hitl_decision import HitlDecision
from revenue_swarm.models.publication import Publication
from revenue_swarm.tasks import TaskName, run_agent_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_agent.agent import generate_content
from content_agent.publish.base import (
    PermanentError,
    PublishTarget,
    TransientError,
    UnknownOutcomeError,
)
from content_agent.publish.registry import TARGETS
from content_agent.settings import (
    MASTODON_TOKEN,
    PUBLISH_ENABLED,
    PUBLISH_MAX_ATTEMPTS,
    PUBLISH_WINDOW_HOURS,
    WORDPRESS_APP_PASSWORD,
    X_BEARER_TOKEN,
)


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


@celery_app.task(name=TaskName.CONTENT_RETRACT.value)
def retract_task(publication_id: str) -> None:
    db = SessionLocal()
    try:
        pub = db.get(Publication, uuid.UUID(publication_id))
        if pub is None or pub.status != PublicationStatus.SUCCEEDED.value:
            return
        item = db.get(ContentItem, pub.content_item_id)
        if pub.external_id:
            TARGETS[pub.target]().retract(pub.external_id)
        pub.status = PublicationStatus.RETRACTED.value
        if item is not None:
            item.status = ContentStatus.APPROVED.value
        db.commit()
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


SECRETS = tuple(
    s for s in (WORDPRESS_APP_PASSWORD, X_BEARER_TOKEN, MASTODON_TOKEN) if s
)


def redact(text: str) -> str:
    for secret in SECRETS:
        text = text.replace(secret, "***")
    return text[:200]


def _fail(
    db: Session, pub: Publication, exc: Exception, *, retryable: bool
) -> None:
    pub.status = PublicationStatus.FAILED.value
    pub.error = redact(str(exc))
    pub.payload = {**(pub.payload or {}), "retryable": retryable}
    db.commit()


def _needs_review(db: Session, pub: Publication, exc: Exception) -> None:
    pub.status = PublicationStatus.NEEDS_REVIEW.value
    pub.error = redact(str(exc))
    db.commit()


def _deliver(
    db: Session, item: ContentItem, pub: Publication, target: PublishTarget
) -> str:
    try:
        result = target.publish(item)
    except TransientError as e:
        _fail(db, pub, e, retryable=True)
        return "failed"
    except UnknownOutcomeError as e:
        _needs_review(db, pub, e)
        return "needs_review"
    except PermanentError as e:
        _fail(db, pub, e, retryable=False)
        return "failed"
    pub.status = PublicationStatus.SUCCEEDED.value
    pub.external_id = result.external_id
    pub.external_url = result.url
    pub.payload = result.payload
    item.status = ContentStatus.PUBLISHED.value
    item.published_at = datetime.now(UTC)
    db.commit()
    return "succeeded"


def may_publish(db: Session, item: ContentItem) -> str | None:
    """Returns a reason to skip, or None when publishing is allowed"""
    if not PUBLISH_ENABLED:
        return "PUBLISH_ENABLED=0"
    if item.status != ContentStatus.SCHEDULED.value:
        return f"status={item.status}"
    if item.scheduled_for is None or item.scheduled_for > datetime.now(UTC):
        return "not due yet"
    if not _has_hitl_approval(db, item.id):
        return "no HITL approval on record"
    if not _within_window(datetime.now(UTC)):
        return "outside publishing window"
    return None


def _has_hitl_approval(db: Session, content_id: uuid.UUID) -> bool:
    stmt = select(HitlDecision.id).where(
        HitlDecision.entity_type == HitlEntityType.CONTENT_ITEM.value,
        HitlDecision.entity_id == content_id,
        HitlDecision.decision == HitlDecisionValue.APPROVED.value,
    )
    return db.scalar(stmt) is not None


def _within_window(now: datetime) -> bool:
    start_s, end_s = PUBLISH_WINDOW_HOURS.split("-", maxsplit=1)
    start, end = int(start_s), int(end_s)
    return start <= now.hour < end

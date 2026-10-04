import os
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from revenue_swarm.celery import celery_app
from revenue_swarm.db import get_db
from revenue_swarm.enums import ContentStatus, PublicationStatus
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.publication import Publication
from revenue_swarm.tasks import TaskName
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.publication import PublicationRead, ResolvePublication

router = APIRouter(prefix="/publications", tags=["publications"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[PublicationRead])
def list_publications(
    db: DbSession,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Publication]:
    stmt = select(Publication).order_by(Publication.updated_at.desc())
    if status:
        stmt = stmt.where(Publication.status == status)
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/needs-review", response_model=list[PublicationRead])
def list_needs_review(db: DbSession) -> list[Publication]:
    stmt = (
        select(Publication)
        .where(Publication.status == PublicationStatus.NEEDS_REVIEW.value)
        .order_by(Publication.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/meta")
def publication_meta() -> dict[str, bool]:
    enabled = os.getenv("PUBLISH_ENABLED", "0") == "1"
    return {"publish_enabled": enabled}


@router.post("/{publication_id}/resolve", response_model=PublicationRead)
def resolve_publication(
    publication_id: uuid.UUID, body: ResolvePublication, db: DbSession
) -> Publication:
    pub = db.get(Publication, publication_id)
    if pub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    if pub.status != PublicationStatus.NEEDS_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot resolve {pub.status}",
        )
    item = db.get(ContentItem, pub.content_item_id)
    if body.resolution == "published":
        if not body.external_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="external_id is required",
            )
        pub.status = PublicationStatus.SUCCEEDED.value
        pub.external_id = body.external_id
        pub.external_url = body.external_url
        if item is not None:
            item.status = ContentStatus.PUBLISHED.value
            item.published_at = datetime.now(UTC)
    else:
        pub.status = PublicationStatus.FAILED.value
        pub.error = None
        pub.payload = {**(pub.payload or {}), "retryable": True}
    db.commit()
    db.refresh(pub)
    return pub


@router.post("/{publication_id}/retract", status_code=status.HTTP_202_ACCEPTED)
def retract_publication(publication_id: uuid.UUID) -> dict[str, str]:
    celery_app.send_task(TaskName.CONTENT_RETRACT, args=[str(publication_id)])
    return {"status": "queued"}

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import ContentStatus, HitlDecisionValue, TaskType
from app.models.content_item import ContentItem
from app.models.task import AgentTask
from app.schemas.affiliate_program import HitlAction
from app.schemas.content_item import (
    ContentItemRead,
    ContentRunCreate,
    ContentSchedule,
)
from app.schemas.task import TaskRead
from app.services.hitl import decide_content
from app.workers.content import generate_content_task, publish_due_task

router = APIRouter(prefix="/content", tags=["content"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ContentItemRead])
def list_content(
    db: DbSession,
    status: str | None = Query(default=None),
) -> list[ContentItem]:
    stmt = select(ContentItem).order_by(ContentItem.created_at.desc())
    if status:
        stmt = stmt.where(ContentItem.status == status)
    return list(db.scalars(stmt).all())


@router.post(
    "/run", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED
)
def run_content(db: DbSession, body: ContentRunCreate | None = None):
    limit = body.limit if body else 3
    row = AgentTask(
        type=TaskType.GENERATE_CONTENT.value,
        status="queued",
        input={"limit": limit},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    generate_content_task.delay(str(row.id))
    return row


@router.post("/{content_id}/approve", response_model=ContentItemRead)
def approve_content(
    content_id: uuid.UUID, db: DbSession, body: HitlAction | None = None
):
    return decide_content(
        db,
        content_id,
        HitlDecisionValue.APPROVED,
        body.comment if body else None,
    )


@router.post("/{content_id}/reject", response_model=ContentItemRead)
def reject_content(
    content_id: uuid.UUID, db: DbSession, body: HitlAction | None = None
):
    return decide_content(
        db,
        content_id,
        HitlDecisionValue.REJECTED,
        body.comment if body else None,
    )


@router.post("/{content_id}/schedule", response_model=ContentItemRead)
def schedule_content(
    content_id: uuid.UUID, db: DbSession, body: ContentSchedule | None = None
):
    row = db.get(ContentItem, content_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    if row.status != ContentStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot schedule content in {row.status}",
        )
    row.scheduled_for = (
        body.scheduled_for
        if body and body.scheduled_for
        else datetime.now(UTC)
    )
    row.status = ContentStatus.SCHEDULED.value
    db.commit()
    db.refresh(row)
    return row


@router.post("/publish-due", status_code=status.HTTP_202_ACCEPTED)
def publish_due() -> dict[str, str]:
    publish_due_task.delay()
    return {"status": "queued"}

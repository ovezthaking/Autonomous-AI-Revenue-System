import uuid

from fastapi import HTTPException, status
from revenue_swarm.celery import celery_app
from revenue_swarm.config import EBOOK_MIN_HUMAN_REVIEW
from revenue_swarm.enums import (
    ContentStatus,
    HitlDecisionValue,
    HitlEntityType,
    ProductStatus,
    ProgramStatus,
)
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.hitl_decision import HitlDecision
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName
from sqlalchemy.orm import Session

from app.core.config import HITL_ACTOR
from app.services.discord_hitl import edit_decided_card
from app.services.hitl_subject import subject_from_program
from app.services.webhook import notify_hitl_decision

NOT_FOUND_DETAIL = "Not found"


def _get_program(db: Session, program_id: uuid.UUID) -> AffiliateProgram:
    row = db.get(AffiliateProgram, program_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL
        )
    return row


def _record_decision(
    db: Session,
    entity_type: HitlEntityType,
    entity_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
    actor: str | None = None,
) -> None:
    db.add(
        HitlDecision(
            entity_type=entity_type.value,
            entity_id=entity_id,
            decision=decision.value,
            actor=actor if actor else HITL_ACTOR,
            comment=comment,
        )
    )


def decide_program(
    db: Session,
    program_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
    actor: str | None = None,
) -> AffiliateProgram:
    chosen_actor = actor if actor else HITL_ACTOR
    row = _get_program(db=db, program_id=program_id)
    if row.status != ProgramStatus.PROPOSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Program already {row.status}",
        )
    new_status = (
        ProgramStatus.APPROVED.value
        if decision is HitlDecisionValue.APPROVED
        else ProgramStatus.REJECTED.value
    )
    row.status = new_status
    _record_decision(
        db,
        HitlEntityType.AFFILIATE_PROGRAM,
        row.id,
        decision,
        comment,
        actor=chosen_actor,
    )
    db.commit()
    db.refresh(row)

    notify_hitl_decision(row.name, row.status)
    edit_decided_card(db, subject_from_program(row), chosen_actor)

    return row


def decide_content(
    db: Session,
    content_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
) -> ContentItem:
    row = db.get(ContentItem, content_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL
        )
    if row.status != ContentStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Content already {row.status}",
        )
    row.status = (
        ContentStatus.APPROVED.value
        if decision is HitlDecisionValue.APPROVED
        else ContentStatus.REJECTED.value
    )
    _record_decision(
        db, HitlEntityType.CONTENT_ITEM, row.id, decision, comment
    )
    db.commit()
    db.refresh(row)
    notify_hitl_decision(row.title, row.status)
    return row


# Statuses in which a human decision makes sense. OUTLINING / WRITING are
# in-flight (a worker owns the row) and LIVE / ARCHIVED are terminal.
_DECIDABLE_PRODUCT_STATUSES = (
    ProductStatus.DRAFT.value,
    ProductStatus.OUTLINED.value,
    ProductStatus.ASSEMBLED.value,
)


def decide_product(
    db: Session,
    product_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
    expected_status: str | None = None,
) -> Product:
    """Gate for the ebook pipeline.

    approve on draft     -> outline is generated (status OUTLINING)
    approve on outlined  -> chapters are written (status WRITING)
    approve on assembled -> LIVE, only after a recorded human review
    reject on any of them -> ARCHIVED
    """
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL
        )
    if expected_status is not None and row.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product is {row.status}, not {expected_status}",
        )
    # approve gets a 409 instead of enqueueing the outline twice.
    if row.status not in _DECIDABLE_PRODUCT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot decide {row.status}",
        )

    task: TaskName | None = None
    if decision is HitlDecisionValue.REJECTED:
        row.status = ProductStatus.ARCHIVED.value
    elif row.status == ProductStatus.DRAFT.value:
        row.status = ProductStatus.OUTLINING.value
        task = TaskName.EBOOK_OUTLINE
    elif row.status == ProductStatus.OUTLINED.value:
        row.status = ProductStatus.WRITING.value
        task = TaskName.EBOOK_WRITE
    else:  # ASSEMBLED
        if EBOOK_MIN_HUMAN_REVIEW and not (row.extras or {}).get(
            "reviewed_at"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Human review is required",
            )
        row.status = ProductStatus.LIVE.value

    _record_decision(db, HitlEntityType.PRODUCT, row.id, decision, comment)
    db.commit()
    db.refresh(row)
    # Enqueue only AFTER the commit: the worker guards on the status we
    # just stored, so sending earlier would let it read the old one.
    if task is not None:
        celery_app.send_task(task, args=[str(row.id)])
    notify_hitl_decision(row.title, row.status)
    return row

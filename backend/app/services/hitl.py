import uuid

from fastapi import HTTPException, status
from revenue_swarm.enums import (
    ContentStatus,
    HitlDecisionValue,
    HitlEntityType,
    ProgramStatus,
)
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.hitl_decision import HitlDecision
from sqlalchemy.orm import Session

from app.core.config import HITL_ACTOR
from app.services.webhook import notify_hitl_decision


def _get_program(db: Session, program_id: uuid.UUID) -> AffiliateProgram:
    row = db.get(AffiliateProgram, program_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return row


def _record_decision(
    db: Session,
    entity_type: HitlEntityType,
    entity_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
) -> None:
    db.add(
        HitlDecision(
            entity_type=entity_type.value,
            entity_id=entity_id,
            decision=decision.value,
            actor=HITL_ACTOR,
            comment=comment,
        )
    )


def decide_program(
    db: Session,
    program_id: uuid.UUID,
    decision: HitlDecisionValue,
    comment: str | None,
) -> AffiliateProgram:
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
        db, HitlEntityType.AFFILIATE_PROGRAM, row.id, decision, comment
    )
    db.commit()
    db.refresh(row)

    notify_hitl_decision(row.name, row.status)

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
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
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

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import HITL_ACTOR
from app.core.enums import HitlDecisionValue, HitlEntityType, ProgramStatus
from app.models.affiliate_program import AffiliateProgram
from app.models.hitl_decision import HitlDecision


def _get_program(db: Session, program_id: uuid.UUID) -> AffiliateProgram:
    row = db.get(AffiliateProgram, program_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return row


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
    db.add(
        HitlDecision(
            entity_type=HitlEntityType.AFFILIATE_PROGRAM.value,
            entity_id=row.id,
            decision=decision.value,
            actor=HITL_ACTOR,
            comment=comment,
        )
    )
    db.commit()
    db.refresh(row)
    return row

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import HitlDecisionValue, ProgramStatus
from app.models.affiliate_program import AffiliateProgram
from app.schemas.affiliate_program import (
    HitlAction,
    RecommendationCreate,
    RecommendationRead,
)
from app.services.hitl import decide_program

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=RecommendationRead, status_code=201)
def create_recommendation(
    body: RecommendationCreate, db: DbSession
) -> AffiliateProgram:
    row = AffiliateProgram(
        name=body.name,
        url=body.url,
        network=body.network,
        category=body.category,
        rationale=body.rationale,
        extras=body.extras,
        status=ProgramStatus.PROPOSED.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(
    db: DbSession,
    status_filter: str | None = Query(default="proposed", alias="status"),
) -> list[AffiliateProgram]:
    stmt = select(AffiliateProgram).order_by(
        AffiliateProgram.created_at.desc()
    )
    if status_filter:
        stmt = stmt.where(AffiliateProgram.status == status_filter)
    return list(db.scalars(stmt).all())


@router.get("/{program_id}", response_model=RecommendationRead)
def get_recommendation(
    program_id: uuid.UUID, db: DbSession
) -> AffiliateProgram:
    from fastapi import status

    row = db.get(AffiliateProgram, program_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return row


@router.post("/{program_id}/approve", response_model=RecommendationRead)
def approve_recommendation(
    program_id: uuid.UUID, db: DbSession, body: HitlAction | None = None
) -> AffiliateProgram:
    comment = body.comment if body else None
    return decide_program(db, program_id, HitlDecisionValue.APPROVED, comment)


@router.post("{program_id}/reject", response_model=RecommendationRead)
def reject_recommendation(
    program_id: uuid.UUID, db: DbSession, body: HitlAction | None = None
) -> AffiliateProgram:
    comment = body.comment if body else None
    return decide_program(db, program_id, HitlDecisionValue.REJECTED, comment)

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import ProgramStatus
from app.models.affiliate_program import AffiliateProgram
from app.schemas.affiliate_program import (
    RecommendationCreate,
    RecommendationRead,
)

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

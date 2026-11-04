"""Shop and trends HITL endpoints (/ideas, /listings)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from revenue_swarm.db import get_db
from revenue_swarm.enums import HitlDecisionValue
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.product_listing import ProductListing
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.affiliate_program import HitlAction
from app.schemas.shop import ProductIdeaRead, ProductListingRead
from app.services.hitl import decide_listing, decide_product_idea

router = APIRouter(tags=["shop"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/ideas", response_model=list[ProductIdeaRead])
def list_ideas(db: DbSession, status: str | None = None) -> list[ProductIdea]:
    stmt = select(ProductIdea).order_by(
        ProductIdea.score.desc(), ProductIdea.created_at.desc()
    )
    if status:
        stmt = stmt.where(ProductIdea.status == status)
    return list(db.scalars(stmt).all())


@router.post("/ideas/{idea_id}/approve", response_model=ProductIdeaRead)
def approve_idea(
    idea_id: uuid.UUID,
    db: DbSession,
    action: HitlAction | None = None,
) -> ProductIdea:
    return decide_product_idea(
        db=db,
        idea_id=idea_id,
        decision=HitlDecisionValue.APPROVED,
        comment=action.comment if action else None,
    )


@router.post("/ideas/{idea_id}/reject", response_model=ProductIdeaRead)
def reject_idea(
    idea_id: uuid.UUID,
    db: DbSession,
    action: HitlAction | None = None,
) -> ProductIdea:
    return decide_product_idea(
        db=db,
        idea_id=idea_id,
        decision=HitlDecisionValue.REJECTED,
        comment=action.comment if action else None,
    )


@router.get("/listings", response_model=list[ProductListingRead])
def list_listings(
    db: DbSession, status: str | None = None
) -> list[ProductListing]:
    stmt = select(ProductListing).order_by(ProductListing.created_at.desc())
    if status:
        stmt = stmt.where(ProductListing.status == status)
    return list(db.scalars(stmt).all())


@router.post(
    "/listings/{listing_id}/approve", response_model=ProductListingRead
)
def approve_listing(
    listing_id: uuid.UUID,
    db: DbSession,
    action: HitlAction | None = None,
) -> ProductListing:
    return decide_listing(
        db=db,
        listing_id=listing_id,
        decision=HitlDecisionValue.APPROVED,
        comment=action.comment if action else None,
    )


@router.post(
    "/listings/{listing_id}/reject", response_model=ProductListingRead
)
def reject_listing(
    listing_id: uuid.UUID,
    db: DbSession,
    action: HitlAction | None = None,
) -> ProductListing:
    return decide_listing(
        db=db,
        listing_id=listing_id,
        decision=HitlDecisionValue.REJECTED,
        comment=action.comment if action else None,
    )

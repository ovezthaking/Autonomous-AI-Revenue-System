import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from revenue_swarm import storage
from revenue_swarm.celery import celery_app
from revenue_swarm.db import get_db
from revenue_swarm.enums import HitlDecisionValue, ProductStatus
from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.product import (
    ChapterRead,
    ProductDecision,
    ProductProposeCreate,
    ProductRead,
    ProductReview,
)
from app.services.hitl import decide_product

router = APIRouter(prefix="/products", tags=["products"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_product(db: Session, product_id: uuid.UUID) -> Product:
    row = db.get(Product, product_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return row


@router.get("", response_model=list[ProductRead])
def list_products(
    db: DbSession, status: str | None = Query(default=None)
) -> list[Product]:
    stmt = select(Product).order_by(Product.created_at.desc())
    if status:
        stmt = stmt.where(Product.status == status)
    return list(db.scalars(stmt).all())


@router.post("/propose", status_code=status.HTTP_202_ACCEPTED)
def propose_products(body: ProductProposeCreate) -> dict[str, str]:
    celery_app.send_task(TaskName.EBOOK_PROPOSE, args=[body.niche])
    return {"status": "queued"}


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: uuid.UUID, db: DbSession) -> Product:
    return _get_product(db, product_id)


@router.get("/{product_id}/chapters", response_model=list[ChapterRead])
def list_chapters(product_id: uuid.UUID, db: DbSession) -> list[EbookChapter]:
    """The outline a human reviews before approving the writing step."""
    _get_product(db, product_id)
    stmt = (
        select(EbookChapter)
        .where(EbookChapter.product_id == product_id)
        .order_by(EbookChapter.position.asc())
    )
    return list(db.scalars(stmt).all())


@router.post("/{product_id}/approve", response_model=ProductRead)
def approve_product(
    product_id: uuid.UUID, db: DbSession, body: ProductDecision
) -> Product:
    return decide_product(
        db,
        product_id,
        HitlDecisionValue.APPROVED,
        body.comment,
        body.expected_status,
    )


@router.post("/{product_id}/reject", response_model=ProductRead)
def reject_product(
    product_id: uuid.UUID, db: DbSession, body: ProductDecision
) -> Product:
    return decide_product(
        db,
        product_id,
        HitlDecisionValue.REJECTED,
        body.comment,
        body.expected_status,
    )


@router.post("/{product_id}/review", response_model=ProductRead)
def record_review(
    product_id: uuid.UUID, body: ProductReview, db: DbSession
) -> Product:
    """Records who read the finished book; required before going LIVE."""
    row = _get_product(db, product_id)
    if row.status != ProductStatus.ASSEMBLED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot review {row.status}",
        )
    row.extras = {
        **(row.extras or {}),
        "reviewed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reviewed_by": body.reviewer,
    }
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/{product_id}/retry-chapters", status_code=status.HTTP_202_ACCEPTED
)
def retry_failed_chapters(
    product_id: uuid.UUID, db: DbSession
) -> dict[str, str]:
    """Re-queues only the chapters that failed (errata #2)."""
    row = _get_product(db, product_id)
    if row.status != ProductStatus.WRITING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retry {row.status}",
        )
    celery_app.send_task(
        TaskName.EBOOK_WRITE, args=[str(row.id)], kwargs={"retry_failed": True}
    )
    return {"status": "queued"}


@router.get("/{product_id}/asset-url")
def get_product_asset_url(
    product_id: uuid.UUID,
    db: DbSession,
    asset_type: str = Query(pattern="^(pdf|epub)$"),
) -> dict[str, str]:
    """Return a presigned download URL for the requested asset."""
    row = _get_product(db, product_id)
    key = row.asset_pdf if asset_type == "pdf" else row.asset_epub
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{asset_type.upper()} asset not found",
        )
    return {"url": storage.presigned_url(key)}

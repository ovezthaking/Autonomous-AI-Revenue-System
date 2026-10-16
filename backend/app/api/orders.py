from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from revenue_swarm.db import get_db
from revenue_swarm.models.order import Order
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.order import OrderRead

router = APIRouter(tags=["orders"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/orders", response_model=list[OrderRead])
def list_orders(db: DbSession) -> list[Order]:
    return list(db.scalars(select(Order).order_by(Order.created_at.desc())))


@router.get("/orders/by-session/{session_id}")
def order_by_session(session_id: str, db: DbSession) -> dict[str, str]:
    order = db.scalar(
        select(Order).where(Order.provider_session_id == session_id)
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return {"id": str(order.id), "status": order.status}

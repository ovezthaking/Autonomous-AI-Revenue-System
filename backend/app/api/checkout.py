from typing import Annotated

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request, status
from revenue_swarm import config
from revenue_swarm.db import get_db
from revenue_swarm.enums import OrderStatus, ProductStatus
from revenue_swarm.models.order import Order
from revenue_swarm.models.product import Product
from revenue_swarm.payments import PaymentProvider, get_payment_provider
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.order import CheckoutRequest

router = APIRouter(tags=["checkout"])
DbSession = Annotated[Session, Depends(get_db)]


def _too_fast(key: str, limit: int = 10) -> bool:
    try:
        client = redis_lib.from_url(
            config.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        )
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, 60)
        return count > limit
    except Exception:
        return False


def provider() -> PaymentProvider:
    return get_payment_provider()


@router.post("/checkout")
def create_checkout(
    payload: CheckoutRequest, request: Request, db: DbSession
) -> dict[str, str]:
    if not config.SALES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sales are disabled",
        )
    ip = request.client.host if request.client else "unknown"
    if _too_fast(f"rl:checkout:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

    product = db.scalar(select(Product).where(Product.slug == payload.slug))
    if product is None or product.status != ProductStatus.LIVE.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not available",
        )

    prov = provider()
    session = prov.create_checkout(
        product, config.SUCCESS_URL, config.CANCEL_URL
    )
    db.add(
        Order(
            product_id=product.id,
            provider=prov.name,
            provider_session_id=session.provider_session_id,
            amount_cents=product.price_cents,
            currency=product.currency,
            status=OrderStatus.PENDING.value,
            consent_immediate_delivery=payload.consent_immediate_delivery,
        )
    )
    db.commit()
    return {"url": session.url, "session_id": session.provider_session_id}

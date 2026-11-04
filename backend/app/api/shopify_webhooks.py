"""Shopify webhook endpoint (/webhooks/shopify) with HMAC verification."""

import base64
import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from revenue_swarm import config
from revenue_swarm.celery import celery_app
from revenue_swarm.config import SHOPIFY_CLIENT_SECRET
from revenue_swarm.db import get_db
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.tasks import TaskName
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(tags=["webhooks"])
DbSession = Annotated[Session, Depends(get_db)]


def verify_shopify_hmac(body: bytes, header: str) -> bool:
    if not header:
        return False
    secret = SHOPIFY_CLIENT_SECRET or config.SHOPIFY_CLIENT_SECRET
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), header)


@router.post("/webhooks/shopify")
async def shopify_webhook(request: Request, db: DbSession) -> dict[str, str]:
    body = await request.body()
    if not verify_shopify_hmac(
        body, request.headers.get("X-Shopify-Hmac-Sha256", "")
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    webhook_id = request.headers.get("X-Shopify-Webhook-Id") or ""
    topic = request.headers.get("X-Shopify-Topic") or ""
    event = PaymentEvent(
        provider="shopify",
        event_id=webhook_id,
        event_type=topic,
        payload=json.loads(body),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    if topic == "orders/paid":
        celery_app.send_task(TaskName.SHOP_FULFILL.value, args=[webhook_id])
    elif topic == "refunds/create":
        celery_app.send_task(TaskName.SHOP_REFUND.value, args=[webhook_id])
    else:
        return {"status": "ignored"}
    return {"status": "accepted"}

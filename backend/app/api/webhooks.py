from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from revenue_swarm.celery import celery_app
from revenue_swarm.db import get_db
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.payments import (
    PaymentProvider,
    SignatureError,
    get_payment_provider,
)
from revenue_swarm.tasks import TaskName
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(tags=["webhooks"])
DbSession = Annotated[Session, Depends(get_db)]


def provider() -> PaymentProvider:
    return get_payment_provider()


@router.post("/webhooks/payments")
async def payments_webhook(request: Request, db: DbSession) -> dict[str, str]:
    body = await request.body()
    prov = provider()
    try:
        note = prov.parse_webhook(body, request.headers)
    except SignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from exc

    event = PaymentEvent(
        provider=prov.name,
        event_id=note.event_id,
        event_type=note.event_type,
        payload=note.raw,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    if note.event_type == "payment_succeeded":
        celery_app.send_task(
            TaskName.SALES_FULFILL.value, args=[note.event_id]
        )
    elif note.event_type == "refunded":
        celery_app.send_task(TaskName.SALES_REFUND.value, args=[note.event_id])
    else:
        return {"status": "ignored"}

    return {"status": "accepted"}

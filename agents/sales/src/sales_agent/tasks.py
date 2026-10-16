import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from revenue_swarm import config
from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.email.resend import send_delivery_email
from revenue_swarm.enums import OrderStatus
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.tasks import TaskName
from sqlalchemy import select
from sqlalchemy.orm import Session


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _event(db: Session, event_id: str) -> PaymentEvent | None:
    return db.scalar(
        select(PaymentEvent).where(PaymentEvent.event_id == event_id)
    )


def _session_id_from(payload: dict[str, Any]) -> str | None:
    # 1. FakeProvider top-level session_id
    if payload.get("session_id"):
        return str(payload["session_id"])
    # 2. Lemon Squeezy meta.custom_data.session_id
    custom = (payload.get("meta") or {}).get("custom_data") or {}
    if custom.get("session_id"):
        return str(custom["session_id"])
    # 3. Stripe checkout.session.completed or charge.refunded
    obj = (payload.get("data") or {}).get("object") or {}
    if payload.get("type") == "charge.refunded":
        if obj.get("checkout_session"):
            return str(obj["checkout_session"])
    elif obj.get("id"):
        return str(obj["id"])
    # 4. Lemon Squeezy fallback data.id
    ls_data = payload.get("data") or {}
    if (
        isinstance(ls_data, dict)
        and ls_data.get("id")
        and "attributes" in ls_data
    ):
        return str(ls_data["id"])
    return None


def _payment_id_from(payload: dict[str, Any]) -> str | None:
    # 1. FakeProvider top-level payment_id
    if payload.get("payment_id"):
        return str(payload["payment_id"])
    # 2. Stripe payment_intent on session/refund events
    obj = (payload.get("data") or {}).get("object") or {}
    if obj.get("payment_intent"):
        return str(obj["payment_intent"])
    if payload.get("type") == "charge.refunded" and obj.get("id"):
        return str(obj["id"])
    # 3. Lemon Squeezy order_number
    attrs = (payload.get("data") or {}).get("attributes") or {}
    if attrs.get("order_number"):
        return str(attrs["order_number"])
    return None


def _order_for(
    db: Session, event: PaymentEvent, *, lock: bool = False
) -> Order | None:
    """Resolve the Order for a webhook event."""
    payload = event.payload or {}
    session_id = _session_id_from(payload)
    payment_id = _payment_id_from(payload)

    if session_id:
        stmt = select(Order).where(Order.provider_session_id == session_id)
        if lock:
            stmt = stmt.with_for_update()
        order = db.scalar(stmt)
        if order is not None:
            return order

    if payment_id:
        stmt = select(Order).where(Order.provider_payment_id == payment_id)
        if lock:
            stmt = stmt.with_for_update()
        order = db.scalar(stmt)
        if order is not None:
            return order

    return None


def _amount_matches(order: Order, event: PaymentEvent) -> bool:
    """Compare order price against net amount before tax."""
    payload = event.payload or {}
    # 1. FakeProvider / explicit net fields
    amount = (
        payload.get("subtotal")
        if payload.get("subtotal") is not None
        else payload.get("amount_cents")
    )
    # 2. Stripe object: prefer amount_subtotal over amount_total
    if amount is None:
        obj = (payload.get("data") or {}).get("object") or {}
        amount = (
            obj.get("amount_subtotal")
            if obj.get("amount_subtotal") is not None
            else obj.get("amount_total")
        )
    # 3. Lemon Squeezy attributes: prefer subtotal over total
    if amount is None:
        attrs = (payload.get("data") or {}).get("attributes") or {}
        amount = (
            attrs.get("subtotal")
            if attrs.get("subtotal") is not None
            else attrs.get("total")
        )
    return amount == order.amount_cents


def _flag(db: Session, order: Order, reason: str) -> None:
    order.extras = {**(order.extras or {}), "needs_review": reason}
    db.commit()


def _email_from(event: PaymentEvent) -> str | None:
    payload = event.payload or {}
    if payload.get("email"):
        return str(payload["email"])
    obj = (payload.get("data") or {}).get("object") or {}
    cust = obj.get("customer_details") or {}
    if cust.get("email"):
        return str(cust["email"])
    attrs = (payload.get("data") or {}).get("attributes") or {}
    if attrs.get("user_email"):
        return str(attrs["user_email"])
    return None


def create_grant(db: Session, order: Order) -> tuple[str, DownloadGrant]:
    token = secrets.token_urlsafe(32)
    grant = DownloadGrant(
        order_id=order.id,
        token_hash=sha256_hex(token),
        expires_at=datetime.now(UTC)
        + timedelta(days=config.DOWNLOAD_TOKEN_TTL_DAYS),
        max_downloads=config.DOWNLOAD_MAX_PER_GRANT,
    )
    db.add(grant)
    db.commit()
    return token, grant


def _grants(db: Session, order_id: uuid.UUID) -> list[DownloadGrant]:
    return list(
        db.scalars(
            select(DownloadGrant).where(DownloadGrant.order_id == order_id)
        ).all()
    )


@celery_app.task(name=TaskName.SALES_FULFILL.value, soft_time_limit=120)
def fulfill_task(event_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        event = _event(db, event_id)
        if event is None:
            return {"status": "event_not_found"}
        # acquire row-level lock on Order to prevent race condition
        order = _order_for(db, event, lock=True)
        if order is None:
            event.payload = {
                **(event.payload or {}),
                "needs_review": "order_not_found",
            }
            db.commit()
            return {"status": "order_not_found"}
        if order.status == OrderStatus.FULFILLED.value:
            return {"status": "already_fulfilled"}
        if not _amount_matches(order, event):
            _flag(db, order, "amount mismatch")
            return {"status": "needs_review"}

        order.status = OrderStatus.PAID.value
        order.email = order.email or _email_from(event)
        # persist provider_payment_id so future refund events match
        payment_id = _payment_id_from(event.payload or {})
        if payment_id:
            order.provider_payment_id = payment_id
        db.commit()

        token, _grant = create_grant(db, order)
        send_delivery_email(order, token)
        order.status = OrderStatus.FULFILLED.value
        order.fulfilled_at = datetime.now(UTC)
        event.processed_at = datetime.now(UTC)
        db.commit()
        return {"status": "fulfilled"}
    finally:
        db.close()


@celery_app.task(name=TaskName.SALES_REFUND.value)
def refund_task(event_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        event = _event(db, event_id)
        if event is None:
            return {"status": "event_not_found"}
        order = _order_for(db, event, lock=True)
        if order is None:
            return {"status": "order_not_found"}
        order.status = OrderStatus.REFUNDED.value
        for grant in _grants(db, order.id):
            grant.revoked = True
        event.processed_at = datetime.now(UTC)
        db.commit()
        return {"status": "refunded"}
    finally:
        db.close()

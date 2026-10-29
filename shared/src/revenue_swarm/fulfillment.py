"""Shared digital order fulfillment (grant creation + delivery email)."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from revenue_swarm import config
from revenue_swarm.email.resend import send_delivery_email
from revenue_swarm.enums import OrderStatus
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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


def fulfill_order(db: Session, order: Order) -> int:
    locked = db.scalar(
        select(Order).where(Order.id == order.id).with_for_update()
    )
    if locked is None or locked.status == OrderStatus.FULFILLED.value:
        return 0
    locked.status = OrderStatus.PAID.value
    db.commit()
    token, _grant = create_grant(db, locked)
    send_delivery_email(locked, token)
    locked.status = OrderStatus.FULFILLED.value
    locked.fulfilled_at = datetime.now(UTC)
    db.commit()
    return 1

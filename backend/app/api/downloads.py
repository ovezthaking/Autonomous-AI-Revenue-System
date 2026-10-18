import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated, Any, cast

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from revenue_swarm import config, storage
from revenue_swarm.db import get_db
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.product import Product
from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)
router = APIRouter(tags=["downloads"])
DbSession = Annotated[Session, Depends(get_db)]


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _too_fast(key: str, limit: int = 10) -> bool:
    try:
        client = redis_lib.from_url(
            config.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        )
        count = cast(int, client.incr(key))
        if count == 1:
            client.expire(key, 60)
        return count > limit
    except Exception:
        return False


def _validate_grant(
    db: Session, token: str, *, lock: bool = False
) -> tuple[DownloadGrant, Order, Product]:
    stmt = select(DownloadGrant).where(
        DownloadGrant.token_hash == sha256_hex(token)
    )
    if lock:
        stmt = stmt.with_for_update()
    grant = db.scalar(stmt)
    if grant is None or grant.revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        )
    expires_at = grant.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Link expired"
        )
    if grant.downloads >= grant.max_downloads:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Download limit reached",
        )
    order = db.get(Order, grant.order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    product = db.get(Product, order.product_id)
    if product is None or not product.asset_pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return grant, order, product


@router.get("/download/{token}")
def verify_download_link(
    token: str, request: Request, db: DbSession
) -> dict[str, Any]:
    """GET only verifies the grant without consuming a download.

    Automated email scanners (Gmail/Outlook link prefetchers) issue GET
    requests when an email arrives. Incrementing only happens on POST.
    """
    ip = request.client.host if request.client else "unknown"
    if _too_fast(f"rl:download:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )
    grant, _order, product = _validate_grant(db, token, lock=False)
    return {
        "status": "ready",
        "title": product.title,
        "slug": product.slug,
        "downloads_used": grant.downloads,
        "max_downloads": grant.max_downloads,
        "remaining_downloads": grant.max_downloads - grant.downloads,
        "expires_at": grant.expires_at.isoformat(),
    }


@router.post("/download/{token}")
def consume_download_link(
    token: str, request: Request, db: DbSession
) -> Response:
    """POST consumes 1 download and issues a 5-min presigned URL."""
    ip = request.client.host if request.client else "unknown"
    if _too_fast(f"rl:download:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )
    grant, _order, product = _validate_grant(db, token, lock=True)
    grant.downloads += 1
    grant.last_ip = request.client.host if request.client else None
    db.commit()
    log.info("download token=%s", token[:8])
    assert product.asset_pdf is not None
    url = storage.presigned_url(product.asset_pdf, expires_in=300)

    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse(
            {
                "url": url,
                "downloads_used": grant.downloads,
                "max_downloads": grant.max_downloads,
                "remaining_downloads": grant.max_downloads - grant.downloads,
            }
        )
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)

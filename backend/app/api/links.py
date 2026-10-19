"""/go/{slug} redirect layer and broken-link repair.

302, never 301: a cached permanent redirect would remove the only reason
this layer exists, which is swapping targets in already-published posts.
"""

import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from revenue_swarm import config
from revenue_swarm.db import get_db
from revenue_swarm.enums import LinkStatus
from revenue_swarm.links import sha256_hex
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.link_click import LinkClick
from revenue_swarm.networks import PermanentNetworkError, network_for
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.affiliate_program import AffiliateLinkRead, LinkRepair

router = APIRouter(tags=["links"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/go/{slug}")
def go(slug: str, request: Request, db: DbSession) -> RedirectResponse:
    if not config.LINK_REDIRECT_ENABLED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Redirects disabled")
    link = db.scalar(select(AffiliateLink).where(AffiliateLink.slug == slug))
    if link is None or link.status == LinkStatus.RETIRED.value:
        return RedirectResponse(config.LINK_FALLBACK_URL, status_code=302)
    user_agent = request.headers.get("user-agent", "")
    try:
        db.add(
            LinkClick(
                link_id=link.id,
                referer=(request.headers.get("referer") or "")[:500] or None,
                user_agent_hash=sha256_hex(user_agent)[:16],
                country=request.headers.get("cf-ipcountry"),
            )
        )
        db.commit()
    except Exception:
        # A lost click is cheaper than a lost redirect.
        db.rollback()
    return RedirectResponse(link.tracking_url, status_code=302)


def _to_read(
    row: AffiliateLink, program: str | None, title: str | None
) -> AffiliateLinkRead:
    return AffiliateLinkRead(
        id=row.id,
        program_id=row.program_id,
        program_name=program,
        content_item_id=row.content_item_id,
        content_title=title,
        destination_url=row.destination_url,
        tracking_url=row.tracking_url,
        slug=row.slug,
        subid=row.subid,
        network=row.network,
        status=row.status,
        last_checked_at=row.last_checked_at,
        created_at=row.created_at,
    )


@router.get("/links", response_model=list[AffiliateLinkRead])
def list_links(
    db: DbSession,
    status_filter: str = Query(default="broken", alias="status"),
) -> list[AffiliateLinkRead]:
    stmt = (
        select(AffiliateLink, AffiliateProgram.name, ContentItem.title)
        .join(
            AffiliateProgram,
            AffiliateProgram.id == AffiliateLink.program_id,
        )
        .outerjoin(
            ContentItem, ContentItem.id == AffiliateLink.content_item_id
        )
        .where(AffiliateLink.status == status_filter)
        .order_by(AffiliateLink.updated_at.desc())
    )
    return [
        _to_read(row, name, title) for row, name, title in db.execute(stmt)
    ]


def _get_link(db: Session, link_id: uuid.UUID) -> AffiliateLink:
    row = db.get(AffiliateLink, link_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return row


@router.patch("/links/{link_id}", response_model=AffiliateLinkRead)
def repair_link(
    link_id: uuid.UUID, body: LinkRepair, db: DbSession
) -> AffiliateLinkRead:
    row = _get_link(db, link_id)
    program = row.program
    try:
        tracking = network_for(row.network).create_link(
            program, body.destination_url, row.subid
        )
    except PermanentNetworkError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Network API unavailable"
        ) from exc
    row.destination_url = body.destination_url
    row.tracking_url = tracking.url
    row.status = LinkStatus.ACTIVE.value
    row.last_checked_at = None
    db.commit()
    db.refresh(row)
    return _to_read(row, program.name, None)


@router.post("/links/{link_id}/retire", response_model=AffiliateLinkRead)
def retire_link(link_id: uuid.UUID, db: DbSession) -> AffiliateLinkRead:
    row = _get_link(db, link_id)
    row.status = LinkStatus.RETIRED.value
    db.commit()
    db.refresh(row)
    return _to_read(row, row.program.name, None)

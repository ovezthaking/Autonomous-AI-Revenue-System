import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from revenue_swarm import config
from revenue_swarm.db import get_db
from revenue_swarm.enums import OrderStatus, PublicationStatus
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.affiliate_metric import AffiliateMetric
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.link_click import LinkClick
from revenue_swarm.models.order import Order
from revenue_swarm.models.publication import Publication
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(tags=["metrics"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/metrics/by-content")
def revenue_by_content(db: DbSession) -> list[dict[str, Any]]:
    items = db.scalars(
        select(ContentItem).order_by(ContentItem.created_at.desc())
    ).all()
    if not items:
        return []

    clicks_by_subid = dict(
        db.execute(
            select(AffiliateLink.subid, func.count(LinkClick.id))
            .join(LinkClick, AffiliateLink.id == LinkClick.link_id)
            .group_by(AffiliateLink.subid)
        ).all()
    )

    metrics_by_subid: dict[str, tuple[int, int, int]] = {}
    for subid, conv, rev_app, rev_pend in db.execute(
        select(
            AffiliateMetric.subid,
            func.coalesce(func.sum(AffiliateMetric.conversions_approved), 0),
            func.coalesce(func.sum(AffiliateMetric.revenue_approved_cents), 0),
            func.coalesce(func.sum(AffiliateMetric.revenue_pending_cents), 0),
        )
        .where(AffiliateMetric.subid.is_not(None))
        .group_by(AffiliateMetric.subid)
    ).all():
        if subid:
            metrics_by_subid[str(subid)] = (
                int(conv),
                int(rev_app),
                int(rev_pend),
            )

    pub_by_item: dict[uuid.UUID, str | None] = {}
    for item_id, ext_url in db.execute(
        select(Publication.content_item_id, Publication.external_url).where(
            Publication.status == PublicationStatus.SUCCEEDED.value
        )
    ).all():
        if item_id not in pub_by_item and ext_url:
            pub_by_item[item_id] = ext_url

    own_by_subid = dict(
        db.execute(
            select(
                Order.source, func.coalesce(func.sum(Order.amount_cents), 0)
            )
            .where(
                Order.source.is_not(None),
                Order.status == OrderStatus.FULFILLED.value,
            )
            .group_by(Order.source)
        ).all()
    )

    rows: list[dict[str, Any]] = []
    for item in items:
        subid = item.id.hex
        conv, aff_cents, pend_cents = metrics_by_subid.get(subid, (0, 0, 0))
        tokens = int((item.extras or {}).get("tokens_used") or 0)
        rows.append(
            {
                "id": str(item.id),
                "title": item.title,
                "publication": pub_by_item.get(item.id),
                "clicks": int(clicks_by_subid.get(subid, 0)),
                "conversions": conv,
                "affiliate_cents": aff_cents,
                "own_cents": int(own_by_subid.get(subid, 0)),
                "pending_cents": pend_cents,
                "cost_cents": tokens * config.TOKEN_CENTS,
            }
        )
    return rows

import uuid
from datetime import date, timedelta
from decimal import Decimal

from revenue_swarm import config
from revenue_swarm.models.affiliate_metric import AffiliateMetric
from sqlalchemy import select
from sqlalchemy.orm import Session


def _aggregate(
    db: Session, program_id: uuid.UUID, window_days: int
) -> tuple[int, int]:
    since = date.today() - timedelta(days=window_days)
    rows = db.scalars(
        select(AffiliateMetric).where(
            AffiliateMetric.program_id == program_id,
            AffiliateMetric.day >= since,
        )
    ).all()
    clicks = sum(row.clicks for row in rows)
    revenue = sum(row.revenue_approved_cents for row in rows)
    return clicks, revenue


def real_epc(
    db: Session, program_id: uuid.UUID, window_days: int = 90
) -> Decimal | None:
    clicks, revenue = _aggregate(db, program_id, window_days)
    if clicks < config.MIN_CLICKS_FOR_EPC:
        return None
    return Decimal(revenue) / Decimal(clicks) / Decimal(100)


def smoothed_epc(
    clicks: int,
    revenue_cents: int,
    category_epc: float,
    prior_weight: int = 100,
) -> float:
    return (revenue_cents / 100 + category_epc * prior_weight) / (
        clicks + prior_weight
    )

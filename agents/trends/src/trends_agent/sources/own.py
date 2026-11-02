"""Own content revenue signal source."""

from revenue_swarm.enums import OrderStatus
from revenue_swarm.models.affiliate_metric import AffiliateMetric
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.order import Order
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

_PRINTABLE_WORDS = ("planner", "checklist", "tracker", "workbook", "printable")


def _affiliate_cents(db: Session, subid: str) -> int:
    aff = int(
        db.scalar(
            select(
                func.coalesce(
                    func.sum(AffiliateMetric.revenue_approved_cents), 0
                )
            ).where(AffiliateMetric.subid == subid)
        )
        or 0
    )
    own = int(
        db.scalar(
            select(func.coalesce(func.sum(Order.amount_cents), 0)).where(
                Order.source == subid,
                Order.status == OrderStatus.FULFILLED.value,
            )
        )
        or 0
    )
    return aff + own


def _normalize_printable_term(title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in _PRINTABLE_WORDS):
        return title
    return f"{title} printable checklist"


class OwnSource:
    name = "own"

    def collect(self, db: Session) -> list[TrendSignal]:
        items = db.scalars(select(ContentItem)).all()
        signals: list[TrendSignal] = []
        for item in items:
            cents = _affiliate_cents(db, item.id.hex)
            if cents <= 0:
                continue
            signals.append(
                TrendSignal(
                    source=self.name,
                    term=_normalize_printable_term(item.title),
                    value=float(cents),
                    window_days=90,
                    raw={
                        "content_item_id": str(item.id),
                        "base_title": item.title,
                    },
                )
            )
        return signals

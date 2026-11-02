"""Deterministic product idea scoring and feature extraction."""

from revenue_swarm.models.affiliate_metric import AffiliateMetric
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

WEIGHTS: dict[str, float] = {
    "own_fit": 0.35,
    "demand": 0.25,
    "producibility": 0.25,
    "competition": 0.15,
}


def score_idea(
    features: dict[str, float],
) -> tuple[float, dict[str, float]]:
    breakdown = {k: round(features[k] * w, 4) for k, w in WEIGHTS.items()}
    return round(sum(breakdown.values()), 4), breakdown


def features_for(db: Session, term: str) -> dict[str, float]:
    return {
        "own_fit": _own_fit(db, term),
        "demand": _demand(db, term),
        "producibility": 1.0 if _is_printable(term) else 0.0,
        "competition": _competition(db, term),
    }


def _is_printable(term: str) -> bool:
    words = ("planner", "checklist", "tracker", "workbook", "printable")
    lowered = term.lower()
    return any(word in lowered for word in words)


def _own_fit(db: Session, term: str) -> float:
    lowered = term.lower()
    # 1. Check direct own signal
    own_signal = db.scalar(
        select(TrendSignal)
        .where(
            TrendSignal.source == "own",
            func.lower(TrendSignal.term) == lowered,
            TrendSignal.value > 0,
        )
        .limit(1)
    )
    if own_signal is not None:
        return 1.0

    # 2. Check ContentItem with positive affiliate revenue
    items = db.scalars(select(ContentItem)).all()
    for item in items:
        title_low = item.title.strip().lower()
        if not title_low:
            continue
        if title_low in lowered or lowered in title_low:
            rev = int(
                db.scalar(
                    select(
                        func.coalesce(
                            func.sum(AffiliateMetric.revenue_approved_cents),
                            0,
                        )
                    ).where(AffiliateMetric.subid == item.id.hex)
                )
                or 0
            )
            if rev > 0:
                return 1.0
    return 0.0


def _demand(db: Session, term: str) -> float:
    signal = db.scalar(
        select(TrendSignal)
        .where(func.lower(TrendSignal.term) == term.lower())
        .order_by(TrendSignal.captured_at.desc())
        .limit(1)
    )
    if signal is None or signal.value <= 0:
        return 0.0
    val = float(signal.value)
    if val <= 1.0:
        return round(min(max(val, 0.0), 1.0), 4)
    return round(min(val / 100.0, 1.0), 4)


def _competition(db: Session, term: str) -> float:
    signal = db.scalar(
        select(TrendSignal)
        .where(
            func.lower(TrendSignal.term) == term.lower(),
            TrendSignal.source == "search",
        )
        .order_by(TrendSignal.captured_at.desc())
        .limit(1)
    )
    if signal is None:
        return 0.5
    raw = signal.raw or {}
    count = int(raw.get("result_count", 10))
    return round(min(max(1.0 - (count / 20.0), 0.0), 1.0), 4)

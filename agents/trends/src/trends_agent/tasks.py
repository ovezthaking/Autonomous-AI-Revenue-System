"""Celery tasks for trends-agent (collect demand signals and propose ideas)."""

from revenue_swarm import config
from revenue_swarm.celery import celery_app
from revenue_swarm.config import (
    TRENDS_ENABLED,
    TRENDS_MAX_IDEAS_PER_RUN,
)
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import IdeaStatus, ProductKind
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.trend_signal import TrendSignal
from revenue_swarm.tasks import TaskName
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trends_agent.ip_filter import ip_risk
from trends_agent.score import features_for, score_idea
from trends_agent.sources import active_sources


def _recent_terms(db: Session) -> list[str]:
    rows = db.scalars(
        select(TrendSignal.term).order_by(TrendSignal.captured_at.desc())
    ).all()
    seen: set[str] = set()
    terms: list[str] = []
    for raw in rows:
        term = raw.strip()
        key = term.lower()
        if not term or key in seen:
            continue
        seen.add(key)
        terms.append(term)
    return terms


def _idea_exists(db: Session, term: str) -> bool:
    existing = db.scalar(
        select(ProductIdea.id)
        .where(func.lower(ProductIdea.term) == term.lower())
        .limit(1)
    )
    return existing is not None


@celery_app.task(name=TaskName.TRENDS_COLLECT.value)
def collect_task() -> dict[str, int]:
    if not (TRENDS_ENABLED or config.TRENDS_ENABLED):
        return {"signals": 0}
    db = SessionLocal()
    try:
        written = 0
        for source in active_sources():
            for signal in source.collect(db):
                db.add(signal)
                written += 1
        db.commit()
        return {"signals": written}
    finally:
        db.close()


@celery_app.task(name=TaskName.TRENDS_PROPOSE.value)
def propose_task() -> dict[str, int]:
    if not (TRENDS_ENABLED or config.TRENDS_ENABLED):
        return {"proposed": 0}
    db = SessionLocal()
    try:
        proposed = 0
        for term in _recent_terms(db):
            if proposed >= TRENDS_MAX_IDEAS_PER_RUN:
                break
            if _idea_exists(db, term):
                continue
            features = features_for(db, term)
            if features["producibility"] == 0:
                continue
            risk = ip_risk(term)
            if risk:
                db.add(
                    ProductIdea(
                        term=term,
                        title=term,
                        kind=ProductKind.PRINTABLE.value,
                        score=0,
                        score_breakdown={},
                        status=IdeaStatus.BLOCKED.value,
                        blocked_reason=risk,
                    )
                )
                continue
            total, breakdown = score_idea(features)
            db.add(
                ProductIdea(
                    term=term,
                    title=term,
                    kind=ProductKind.PRINTABLE.value,
                    score=total,
                    score_breakdown=breakdown,
                    status=IdeaStatus.PROPOSED.value,
                )
            )
            proposed += 1
        db.commit()
        return {"proposed": proposed}
    finally:
        db.close()

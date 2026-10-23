import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from revenue_swarm import config
from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import ApplicationStatus, LinkStatus, ProgramStatus
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.affiliate_metric import AffiliateMetric
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.link_click import LinkClick
from revenue_swarm.networks import PerformanceRow, active_networks
from revenue_swarm.tasks import TaskName, run_agent_task
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from research_agent.agent import discover_programs_v1, discover_programs_v2
from research_agent.epc import _aggregate, real_epc, smoothed_epc
from research_agent.models import ProgramFacts
from research_agent.probe import probe
from research_agent.score import score_program
from research_agent.settings import RESEARCH_SOURCE


@celery_app.task(
    name=TaskName.RESEARCH_DISCOVER.value,
    soft_time_limit=600,
    time_limit=660,
)
def discover_programs_task(task_id: str) -> None:
    def handler(db, row):
        limit = int(row.input.get("limit", 10))
        if RESEARCH_SOURCE == "catalog":
            return discover_programs_v1(db, row.id, limit)
        return discover_programs_v2(db, row.id, limit)

    run_agent_task(task_id, handler)


def _epc_source(
    db: Session, row: AffiliateProgram, extras: dict[str, Any]
) -> tuple[float | None, str]:
    measured = real_epc(db, row.id, config.EPC_WINDOW_DAYS)
    if measured is not None:
        clicks, revenue = _aggregate(db, row.id, config.EPC_WINDOW_DAYS)
        category = float(extras.get("category_epc") or 0)
        value = smoothed_epc(
            clicks, revenue, category, config.EPC_PRIOR_WEIGHT
        )
        return value, "own"
    manual = extras.get("epc_operator")
    if isinstance(manual, int | float) and not isinstance(manual, bool):
        return float(manual), "operator"
    legacy = extras.get("epc")
    if (
        extras.get("epc_source") != "own"
        and isinstance(legacy, int | float)
        and not isinstance(legacy, bool)
    ):
        return float(legacy), "operator"
    return None, "declared"


def rescore_proposed(db: Session) -> int:
    """Recomputes score for proposed programs using prioritized EPC."""
    rows = db.scalars(
        select(AffiliateProgram).where(
            AffiliateProgram.status == ProgramStatus.PROPOSED.value
        )
    ).all()
    updated = 0
    for row in rows:
        extras = dict(row.extras or {})
        raw_facts = extras.get("facts")
        if not isinstance(raw_facts, dict):
            continue
        payload = dict(raw_facts)
        payload.setdefault("program_name", row.name)
        try:
            facts = ProgramFacts.model_validate(payload)
        except ValidationError:
            continue
        has_legacy_only = (
            "epc" in extras
            and "epc_operator" not in extras
            and real_epc(db, row.id, config.EPC_WINDOW_DAYS) is None
        )
        epc, source = _epc_source(db, row, extras)
        if epc is not None:
            extras["epc"] = epc
        extras["epc_source"] = source
        total, breakdown_floats = score_program(facts, epc=epc)
        breakdown: dict[str, Any] = dict(breakdown_floats)
        if not has_legacy_only:
            breakdown["epc_source"] = source
        extras["score_breakdown"] = breakdown
        row.score = total
        row.extras = extras
        updated += 1
    return updated


@celery_app.task(name=TaskName.RESEARCH_RESCORE.value)
def rescore_task() -> int:
    """Recomputes score for all proposed programs, honouring operator EPC."""
    db = SessionLocal()
    try:
        updated = rescore_proposed(db)
        db.commit()
        return updated
    finally:
        db.close()


def _resolve_program_id(
    db: Session, network: str, raw_program_id: str | None
) -> uuid.UUID | None:
    if not raw_program_id:
        return None
    found = db.scalar(
        select(AffiliateProgram.id).where(
            AffiliateProgram.network == network,
            AffiliateProgram.network_program_id == raw_program_id,
        )
    )
    if found is not None:
        return found
    try:
        candidate = uuid.UUID(str(raw_program_id))
    except ValueError:
        return None
    program = db.get(AffiliateProgram, candidate)
    return program.id if program is not None else None


def _upsert_metric(db: Session, network: str, row: PerformanceRow) -> None:
    program_id = _resolve_program_id(db, network, row.program_id)
    values = {
        "network": network,
        "program_id": program_id,
        "subid": row.subid,
        "day": row.day,
        "clicks": row.clicks,
        "conversions_pending": row.conversions_pending,
        "conversions_approved": row.conversions_approved,
        "conversions_declined": row.conversions_declined,
        "revenue_pending_cents": row.revenue_pending_cents,
        "revenue_approved_cents": row.revenue_approved_cents,
        "currency": row.currency,
        "synced_at": datetime.now(UTC),
    }
    stmt = insert(AffiliateMetric).values(**values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metric_day",
        set_=values,
    )
    db.execute(stmt)


def sync_performance(db: Session, days_back: int = 7) -> dict[str, int]:
    until = date.today()
    since = until - timedelta(days=days_back)
    written = 0
    for network in active_networks():
        for row in network.fetch_performance(since, until):
            _upsert_metric(db, network.name, row)
            written += 1
    db.commit()
    return {"rows": written}


@celery_app.task(name=TaskName.AFFILIATE_SYNC.value, soft_time_limit=900)
def sync_performance_task(days_back: int = 7) -> dict[str, int]:
    db = SessionLocal()
    try:
        return sync_performance(db, days_back=days_back)
    finally:
        db.close()


def check_pending(db: Session, now: datetime | None = None) -> dict[str, int]:
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(days=14)
    rows = db.scalars(
        select(AffiliateProgram).where(
            AffiliateProgram.application_status
            == ApplicationStatus.PENDING.value,
            AffiliateProgram.applied_at < cutoff,
        )
    ).all()
    for row in rows:
        row.extras = {**(row.extras or {}), "needs_reminder": True}
    db.commit()
    return {"reminders": len(rows)}


@celery_app.task(name=TaskName.AFFILIATE_CHECK_PENDING.value)
def check_pending_task() -> dict[str, int]:
    db = SessionLocal()
    try:
        return check_pending(db)
    finally:
        db.close()


def _active_links(
    db: Session, checked_before: datetime
) -> list[AffiliateLink]:
    stmt = select(AffiliateLink).where(
        AffiliateLink.status == LinkStatus.ACTIVE.value,
        or_(
            AffiliateLink.last_checked_at.is_(None),
            AffiliateLink.last_checked_at < checked_before,
        ),
    )
    return list(db.scalars(stmt).all())


def _flag_for_review(db: Session, link: AffiliateLink, reason: str) -> None:
    if link.content_item_id is None:
        return
    item = db.get(ContentItem, link.content_item_id)
    if item is None:
        return
    item.extras = {**(item.extras or {}), "link_review": reason}


def _silent(db: Session, now: datetime) -> list[AffiliateLink]:
    cutoff = now - timedelta(days=30)
    clicks = (
        select(LinkClick.link_id)
        .where(LinkClick.clicked_at >= cutoff)
        .distinct()
    )
    stmt = select(AffiliateLink).where(
        AffiliateLink.status == LinkStatus.ACTIVE.value,
        AffiliateLink.created_at < cutoff,
        AffiliateLink.id.not_in(clicks),
    )
    return list(db.scalars(stmt).all())


def check_links(db: Session, now: datetime | None = None) -> dict[str, int]:
    if not config.LINK_CHECK_ENABLED:
        return {"checked": 0}
    current = now or datetime.now(UTC)
    links = _active_links(db, checked_before=current - timedelta(days=7))
    broken = 0
    for link in links[: config.LINK_CHECK_BATCH]:
        verdict = probe(link.tracking_url, link.destination_url)
        link.last_checked_at = current
        if verdict.is_broken:
            link.status = LinkStatus.BROKEN.value
            _flag_for_review(db, link, verdict.reason)
            broken += 1
        db.commit()
    for silent_link in _silent(db, current):
        if silent_link.content_item_id is None:
            continue
        item = db.get(ContentItem, silent_link.content_item_id)
        if item is not None:
            item.extras = {**(item.extras or {}), "link_unseen": True}
    db.commit()
    return {
        "checked": min(len(links), config.LINK_CHECK_BATCH),
        "broken": broken,
    }


@celery_app.task(
    name=TaskName.AFFILIATE_CHECK_LINKS.value, soft_time_limit=900
)
def check_links_task() -> dict[str, int]:
    db = SessionLocal()
    try:
        return check_links(db)
    finally:
        db.close()

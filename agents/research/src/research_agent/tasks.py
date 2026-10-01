from pydantic import ValidationError
from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.enums import ProgramStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.tasks import TaskName, run_agent_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from research_agent.agent import discover_programs_v1, discover_programs_v2
from research_agent.models import ProgramFacts
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


def rescore_proposed(db: Session) -> int:
    """Recomputes score for proposed programs, honouring operator EPC."""
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
        raw_epc = extras.get("epc")
        epc = None
        if isinstance(raw_epc, int | float) and not isinstance(raw_epc, bool):
            epc = float(raw_epc)
        total, breakdown = score_program(facts, epc=epc)
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

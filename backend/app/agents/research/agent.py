import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.research.catalog import CANDIDATES, Candidate
from app.core.enums import ProgramStatus
from app.models.affiliate_program import AffiliateProgram
from app.services.llm import generate_rationale

PROMPT_TEMPLATE = (
    "You evaluate affiliate programs for a niche blog about business "
    "software. Program: {name} ({category}, network: {network}, "
    "commission: {commission}). Write two sentences explaining why it is "
    "worth promoting. Be concrete, no marketing fluff, no bullet points."
)


def filter_new_candidates(
    candidates: tuple[Candidate, ...], existing_names: set[str], limit: int
) -> list[Candidate]:
    new_candidates = [c for c in candidates if c.name not in existing_names]
    return new_candidates[:limit]


def _existing_names(
    db: Session, candidates: tuple[Candidate, ...]
) -> set[str]:
    names = [c.name for c in candidates]
    stmt = select(AffiliateProgram.name).where(
        AffiliateProgram.name.in_(names)
    )
    return set(db.scalars(stmt).all())


def discover_programs(
    db: Session,
    task_id: uuid.UUID,
    limit: int = 5,
) -> dict[str, object]:
    existing = _existing_names(db, CANDIDATES)
    selected = filter_new_candidates(CANDIDATES, existing, limit)

    created: list[AffiliateProgram] = []
    for candidate in selected:
        prompt = PROMPT_TEMPLATE.format(
            name=candidate.name,
            category=candidate.category,
            network=candidate.network,
            commission=candidate.commission,
        )
        row = AffiliateProgram(
            name=candidate.name,
            url=candidate.url,
            network=candidate.network,
            category=candidate.category,
            rationale=generate_rationale(prompt),
            extras={
                "commission": candidate.commission,
                "recurring": candidate.recurring,
                "discovered_by": "research_agent_v1",
            },
            status=ProgramStatus.PROPOSED.value,
            source_task_id=task_id,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return {
        "created": len(created),
        "skipped": len(CANDIDATES) - len(selected),
        "program_ids": [str(row.id) for row in created],
    }

import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from revenue_swarm.enums import ProgramStatus
from revenue_swarm.llm import generate_rationale
from revenue_swarm.models.affiliate_program import AffiliateProgram
from sqlalchemy import select
from sqlalchemy.orm import Session

from research_agent.catalog import CANDIDATES, Candidate
from research_agent.extract import extract_facts
from research_agent.fetch import fetch_text
from research_agent.models import Candidate as WebCandidate
from research_agent.score import score_program
from research_agent.search import search
from research_agent.settings import RESEARCH_NICHE
from research_agent.validate import is_usable

PROMPT_TEMPLATE = (
    "You evaluate affiliate programs for a niche blog about business "
    "software. Program: {name} ({category}, network: {network}, "
    "commission: {commission}). Write two sentences explaining why it is "
    "worth promoting. Be concrete, no marketing fluff, no bullet points."
)


def discover_programs_v1(
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


def _existing_names(
    db: Session, candidates: tuple[Candidate, ...]
) -> set[str]:
    names = [c.name for c in candidates]
    stmt = select(AffiliateProgram.name).where(
        AffiliateProgram.name.in_(names)
    )
    return set(db.scalars(stmt).all())


def filter_new_candidates(
    candidates: tuple[Candidate, ...], existing_names: set[str], limit: int
) -> list[Candidate]:
    new_candidates = [c for c in candidates if c.name not in existing_names]
    return new_candidates[:limit]


def discover_programs_v2(
    db: Session, task_id: uuid.UUID, limit: int = 10
) -> dict[str, object]:
    hits = search(RESEARCH_NICHE)
    candidates: list[WebCandidate] = []
    errors: list[dict[str, str]] = []

    for hit in hits:
        try:
            text = hit.raw_content or fetch_text(hit.url)
            if not text:
                errors.append({"url": hit.url, "error": "no content"})
                continue
            facts = extract_facts(hit, text)
            if facts is None or not is_usable(facts, hit.url):
                errors.append({"url": hit.url, "error": "rejected"})
                continue
            total, breakdown = score_program(facts)
            candidates.append(
                WebCandidate(
                    name=facts.program_name.strip(),
                    url=hit.url,
                    evidence_url=hit.url,
                    facts=facts,
                    score=total,
                    score_breakdown=breakdown,
                )
            )
        except Exception as e:
            errors.append({"url": hit.url, "error": str(e)[:200]})

    candidates.sort(key=lambda c: c.score, reverse=True)
    fresh = _drop_known(db, candidates)[:limit]
    created = [_persist(db, c, task_id) for c in fresh]
    db.commit()

    return {
        "hits": len(hits),
        "candidates": len(candidates),
        "created": len(created),
        "errors": errors[:20],
    }


def _drop_known(
    db: Session, candidates: list[WebCandidate]
) -> list[WebCandidate]:
    rows = db.execute(
        select(AffiliateProgram.name, AffiliateProgram.url)
    ).all()
    known_names = {_normalize(name) for name, _url in rows}
    known_hosts = {_host(url) for _name, url in rows if url}
    seen_names: set[str] = set()
    seen_hosts: set[str] = set()
    fresh: list[WebCandidate] = []
    for candidate in candidates:
        name = _normalize(candidate.name)
        host = _host(candidate.url)
        if name in known_names or name in seen_names:
            continue
        if host and (host in known_hosts or host in seen_hosts):
            continue
        seen_names.add(name)
        if host:
            seen_hosts.add(host)
        fresh.append(candidate)
    return fresh


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def _host(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower()


def _persist(
    db: Session, candidate: WebCandidate, task_id: uuid.UUID
) -> AffiliateProgram:
    facts = candidate.facts
    row = AffiliateProgram(
        name=candidate.name,
        url=candidate.url,
        network=facts.network,
        category=facts.category,
        score=candidate.score,
        status=ProgramStatus.PROPOSED.value,
        source_task_id=task_id,
        extras={
            "source": "web",
            "evidence_url": candidate.evidence_url,
            "searched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "facts": facts.model_dump(
                include={
                    "commission_type",
                    "commission_value",
                    "cookie_days",
                    "payout_threshold",
                    "network",
                    "currency",
                    "confidence",
                }
            ),
            "epc": None,
            "epc_source": None,
            "score_breakdown": candidate.score_breakdown,
        },
    )
    db.add(row)
    return row

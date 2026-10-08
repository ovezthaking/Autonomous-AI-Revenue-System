import pytest
from research_agent.agent import discover_programs_v1, discover_programs_v2
from revenue_swarm.enums import ProgramStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_page_fetch(monkeypatch):
    monkeypatch.setattr("research_agent.agent.fetch_text", lambda _url: None)


def test_discover_creates_proposed_programs(db_session, make_task):
    task = make_task(type="research_programs", input={"limit": 3})

    result = discover_programs_v1(db_session, task.id, limit=3)

    assert result["created"] == 3
    rows = db_session.query(AffiliateProgram).all()
    assert len(rows) == 3
    assert all(r.status == ProgramStatus.PROPOSED.value for r in rows)
    assert all(r.source_task_id == task.id for r in rows)
    assert all(r.rationale for r in rows)


def test_discover_is_idempotent_by_name(db_session, make_task):
    task = make_task(type="research_programs", input={"limit": 5})

    first = discover_programs_v1(db_session, task.id, limit=5)
    second = discover_programs_v1(db_session, task.id, limit=5)

    assert isinstance(first["created"], int) and first["created"] > 0
    assert second["created"] == 0


def test_discover_v2_persists_scored_programs_and_rejects_empty_hit(
    db_session, make_task
):
    task = make_task(type="research_programs", input={"limit": 10})

    result = discover_programs_v2(db_session, task.id, limit=10)

    assert result["created"] == 3
    errors = result["errors"]
    assert isinstance(errors, list)
    assert any(
        item["error"] == "rejected" and "roundup.test" in item["url"]
        for item in errors
    )
    rows = db_session.query(AffiliateProgram).all()
    assert len(rows) == 3
    assert all(row.status == ProgramStatus.PROPOSED.value for row in rows)
    assert all(row.score is not None and row.score > 0 for row in rows)
    assert all(row.source_task_id == task.id for row in rows)
    assert all("commission_type" in row.extras["facts"] for row in rows)
    assert all("roundup.test" not in (row.url or "") for row in rows)


def test_discover_v2_second_run_creates_nothing(db_session, make_task):
    task = make_task(type="research_programs", input={"limit": 10})

    first = discover_programs_v2(db_session, task.id, limit=10)
    second = discover_programs_v2(db_session, task.id, limit=10)

    assert first["created"] == 3
    assert second["created"] == 0


def test_rescore_proposed_lets_epc_overtake_public_terms(
    db_session, make_program
):
    from research_agent.models import ProgramFacts
    from research_agent.score import score_program
    from research_agent.tasks import rescore_proposed

    public = {
        "program_name": "High public terms",
        "commission_type": "percent_recurring",
        "commission_value": 25,
        "cookie_days": 90,
        "confidence": 1.0,
    }
    measured = {
        "program_name": "Measured EPC",
        "commission_type": "percent_one_time",
        "commission_value": 25,
        "cookie_days": 30,
        "confidence": 0.0,
    }
    high_public = make_program(
        name="High public terms",
        score=1,
        extras={"facts": public},
    )
    with_epc = make_program(
        name="Measured EPC",
        score=1,
        extras={"facts": measured, "epc": 3.0},
    )
    approved = make_program(
        name="Already approved",
        status="approved",
        score=1,
        extras={"facts": measured, "epc": 3.0},
    )
    make_program(name="No facts", extras={"source": "web"})

    updated = rescore_proposed(db_session)
    db_session.flush()
    db_session.refresh(high_public)
    db_session.refresh(with_epc)
    db_session.refresh(approved)

    public_facts = ProgramFacts.model_validate(public)
    public_score, _breakdown = score_program(public_facts)
    epc_score, epc_breakdown = score_program(
        ProgramFacts.model_validate(measured), epc=3.0
    )
    assert updated == 2
    assert high_public.score == public_score
    assert with_epc.score == epc_score
    assert with_epc.score > high_public.score
    assert with_epc.extras["score_breakdown"] == epc_breakdown
    assert approved.score == 1

import pytest
from research_agent.agent import discover_programs
from revenue_swarm.enums import ProgramStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram

pytestmark = pytest.mark.integration


def test_discover_creates_proposed_programs(db_session, make_task):
    task = make_task(type="research_programs", input={"limit": 3})

    result = discover_programs(db_session, task.id, limit=3)

    assert result["created"] == 3
    rows = db_session.query(AffiliateProgram).all()
    assert len(rows) == 3
    assert all(r.status == ProgramStatus.PROPOSED.value for r in rows)
    assert all(r.source_task_id == task.id for r in rows)
    assert all(r.rationale for r in rows)


def test_discover_is_idempotent_by_name(db_session, make_task):
    task = make_task(type="research_programs", input={"limit": 5})

    first = discover_programs(db_session, task.id, limit=5)
    second = discover_programs(db_session, task.id, limit=5)

    assert first["created"] > 0
    assert second["created"] == 0

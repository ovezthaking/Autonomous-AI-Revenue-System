import pytest
from content_agent.agent import generate_content
from revenue_swarm.models.content_item import ContentItem

pytestmark = pytest.mark.integration

LINK = "https://aff.test/ref?id=1"


def test_generate_content_creates_two_items_per_program(
    db_session, make_task, make_program
):
    make_program(status="approved", affiliate_link=LINK)
    task = make_task(type="generate_content", input={"limit": 3})

    result = generate_content(db_session, task.id, limit=3)

    assert result["programs"] == 1
    assert result["created"] == 2
    items = db_session.query(ContentItem).all()
    assert {i.channel for i in items} == {"blog", "social"}
    assert all(i.status == "draft" for i in items)
    assert all(LINK in i.body for i in items)


def test_generate_content_skips_programs_without_affiliate_link(
    db_session, make_task, make_program
):
    make_program(status="approved", affiliate_link=None)
    task = make_task(type="generate_content", input={"limit": 3})

    result = generate_content(db_session, task.id, limit=3)

    assert result["programs"] == 0
    assert result["created"] == 0
    assert db_session.query(ContentItem).count() == 0


def test_generate_content_skips_proposed_programs(
    db_session, make_task, make_program
):
    make_program(status="proposed", affiliate_link=LINK)
    task = make_task(type="generate_content", input={"limit": 3})

    result = generate_content(db_session, task.id, limit=3)

    assert result["programs"] == 0
    assert result["created"] == 0


def test_generate_content_second_run_creates_nothing(
    db_session, make_task, make_program
):
    make_program(status="approved", affiliate_link=LINK)
    task = make_task(type="generate_content", input={"limit": 3})

    first = generate_content(db_session, task.id, limit=3)
    second = generate_content(db_session, task.id, limit=3)

    assert first["created"] == 2
    assert second["created"] == 0

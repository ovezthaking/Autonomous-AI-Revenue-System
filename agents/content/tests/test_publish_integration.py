from datetime import UTC, datetime, timedelta

import pytest
from content_agent.publish.base import PublishResult
from content_agent.tasks import publish_due_task
from revenue_swarm.enums import HitlDecisionValue, HitlEntityType
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.models.hitl_decision import HitlDecision
from revenue_swarm.models.publication import Publication
from sqlalchemy import select

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def open_gates(monkeypatch):
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", True)
    monkeypatch.setattr("content_agent.tasks.PUBLISH_MIN_INTERVAL_SECONDS", 0)
    monkeypatch.setattr("content_agent.tasks.PUBLISH_WINDOW_HOURS", "0-24")


def test_second_publish_due_does_not_post_again(real_session, monkeypatch):
    calls = {"n": 0}

    class _Target:
        name = "dryrun"

        def publish(self, item):
            calls["n"] += 1
            return PublishResult(
                external_id=f"dryrun-{item.id}", url=None, payload={}
            )

        def retract(self, external_id):
            return None

    monkeypatch.setattr(
        "content_agent.tasks.target_for", lambda _channel: _Target()
    )
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", True)
    monkeypatch.setattr("content_agent.tasks.PUBLISH_MIN_INTERVAL_SECONDS", 0)
    item = _scheduled_with_approval(real_session)
    publish_due_task.run()
    publish_due_task.run()
    rows = real_session.scalars(select(Publication)).all()
    assert len(rows) == 1
    assert rows[0].status == "succeeded"
    assert calls["n"] == 1
    assert item.id == rows[0].content_item_id


def _scheduled_with_approval(session, *, minutes=-5):
    item = ContentItem(
        title="Due post",
        body="Ready.",
        channel="blog",
        status="scheduled",
        scheduled_for=datetime.now(UTC) + timedelta(minutes=minutes),
    )
    session.add(item)
    session.commit()
    session.add(
        HitlDecision(
            entity_type=HitlEntityType.CONTENT_ITEM.value,
            entity_id=item.id,
            decision=HitlDecisionValue.APPROVED.value,
            actor="test-operator",
        )
    )
    session.commit()
    return item


def test_publish_due_publishes_past_items_and_leaves_future_ones(real_session):
    past = _scheduled_with_approval(real_session)
    future = _scheduled_with_approval(real_session, minutes=60)

    result = publish_due_task.run()

    real_session.expire_all()
    assert result == {"published": 1, "skipped": 0, "failed": 0}
    assert real_session.get(ContentItem, past.id).status == "published"
    assert real_session.get(ContentItem, future.id).status == "scheduled"


def test_content_tasks_and_permanent_network_skip(real_session, monkeypatch):
    import uuid

    from content_agent.agent import generate_content
    from content_agent.tasks import generate_content_task, retract_task
    from revenue_swarm.enums import PublicationStatus
    from revenue_swarm.models.affiliate_program import AffiliateProgram
    from revenue_swarm.models.task import AgentTask
    from revenue_swarm.networks import PermanentNetworkError

    # 1. generate_content_task + PermanentNetworkError skip in generate_content
    prog = AffiliateProgram(
        name="SkipProg",
        network="awin",
        status="approved",
        application_status="active",
        affiliate_link="https://aff.test/1",
    )
    task = AgentTask(
        type="generate_content", status="pending", input={"limit": 2}
    )
    real_session.add_all([prog, task])
    real_session.commit()

    def _raise_perm(*_a, **_kw):
        raise PermanentNetworkError("bad network")

    with monkeypatch.context() as m:
        m.setattr("content_agent.agent._items_for", _raise_perm)
        res = generate_content(real_session, task.id, limit=2)
        assert res["skipped"] == [
            {"program": prog.name, "error": "bad network"}
        ]

    generate_content_task.run(str(task.id))

    # 2. publish_due_task: skip, reserve None, publish, and max_per_run break
    unapproved = ContentItem(
        title="No HITL",
        body="Body",
        channel="blog",
        status="scheduled",
        scheduled_for=datetime.now(UTC) - timedelta(minutes=10),
    )
    real_session.add(unapproved)
    real_session.commit()

    already_pub_item = _scheduled_with_approval(real_session, minutes=-9)
    pub = Publication(
        content_item_id=already_pub_item.id,
        target="dryrun",
        status=PublicationStatus.SUCCEEDED.value,
        external_id="dryrun-ext-1",
        attempts=1,
    )
    real_session.add(pub)
    real_session.commit()

    _scheduled_with_approval(real_session, minutes=-8)
    _scheduled_with_approval(real_session, minutes=-7)
    _scheduled_with_approval(real_session, minutes=-6)

    with monkeypatch.context() as m:
        m.setattr("content_agent.tasks.PUBLISH_MAX_PER_RUN", 2)
        out = publish_due_task.run()
        assert out == {"published": 2, "skipped": 2, "failed": 0}

    # 3. retract_task: missing pub and succeeded pub with external_id
    retract_task.run(str(uuid.uuid4()))
    retract_task.run(str(pub.id))
    real_session.expire_all()
    assert (
        real_session.get(Publication, pub.id).status
        == PublicationStatus.RETRACTED.value
    )
    assert (
        real_session.get(ContentItem, already_pub_item.id).status == "approved"
    )

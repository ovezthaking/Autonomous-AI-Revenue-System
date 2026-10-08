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

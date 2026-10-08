import pytest
from content_agent.publish.base import PublishResult
from content_agent.tasks import publish_due_task
from revenue_swarm.models.publication import Publication
from sqlalchemy import select

pytestmark = pytest.mark.integration


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

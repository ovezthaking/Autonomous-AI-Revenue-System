from datetime import UTC, datetime, timedelta

import pytest
from app.models.content_item import ContentItem
from app.workers.content import publish_due_task

pytestmark = pytest.mark.integration


def test_publish_due_publishes_past_items_and_leaves_future_ones(real_session):
    now = datetime.now(UTC)
    past = ContentItem(
        title="Due post",
        body="Ready.",
        channel="blog",
        status="scheduled",
        scheduled_for=now - timedelta(minutes=5),
    )
    future = ContentItem(
        title="Later post",
        body="Not yet.",
        channel="social",
        status="scheduled",
        scheduled_for=now + timedelta(hours=1),
    )
    real_session.add_all([past, future])
    real_session.commit()

    published_count = publish_due_task.run()

    real_session.expire_all()
    past_row = real_session.get(ContentItem, past.id)
    future_row = real_session.get(ContentItem, future.id)
    assert published_count == 1
    assert past_row.status == "published"
    assert past_row.published_at is not None
    assert future_row.status == "scheduled"
    assert future_row.published_at is None

from datetime import UTC, datetime, timedelta

import app.api.content as content_api
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_celery_broker(monkeypatch):
    """Replaces Celery .delay() so API tests do not need a live broker."""
    calls = {"generate": [], "publish": []}

    def _generate(task_id):
        calls["generate"].append(task_id)

    def _publish():
        calls["publish"].append(True)

    monkeypatch.setattr(content_api.generate_content_task, "delay", _generate)
    monkeypatch.setattr(content_api.publish_due_task, "delay", _publish)
    return calls


def test_list_content_returns_empty_list_when_no_items(client):
    response = client.get("/content")
    assert response.status_code == 200
    assert response.json() == []


def test_list_content_returns_items_newest_first(client, make_content_item):
    # created_at has server_default=func.now(); in Postgres now() returns
    # the same value for the entire transaction, so for the "newest
    # first" order to be testable at all, we have to provide explicit,
    # different timestamps instead of relying on the default value.
    now = datetime.now(UTC)
    older = make_content_item(
        title="First post", created_at=now - timedelta(minutes=5)
    )
    newer = make_content_item(title="Second post", created_at=now)

    response = client.get("/content")

    assert response.status_code == 200
    titles = [row["title"] for row in response.json()]
    assert titles.index(newer.title) < titles.index(older.title)


def test_list_content_defaults_to_every_status(client, make_content_item):
    draft = make_content_item(title="Draft post", status="draft")
    published = make_content_item(title="Live post", status="published")

    response = client.get("/content")

    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert draft.title in titles
    assert published.title in titles


def test_list_content_filters_by_status(client, make_content_item):
    draft = make_content_item(title="Draft post", status="draft")
    make_content_item(title="Live post", status="published")

    response = client.get("/content", params={"status": "draft"})

    assert response.status_code == 200
    assert [row["title"] for row in response.json()] == [draft.title]


def test_run_content_returns_202(client, no_celery_broker):
    response = client.post("/content/run", json={"limit": 3})

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "generate_content"
    assert body["status"] == "queued"
    assert no_celery_broker["generate"] == [body["id"]]


def test_approve_content_returns_200(client, make_content_item):
    item = make_content_item(status="draft")

    response = client.post(
        f"/content/{item.id}/approve", json={"comment": "ok"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_schedule_draft_returns_409(client, make_content_item):
    item = make_content_item(status="draft")

    response = client.post(f"/content/{item.id}/schedule", json={})

    assert response.status_code == 409


def test_publish_due_returns_202(client, no_celery_broker):
    response = client.post("/content/publish-due")

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert no_celery_broker["publish"] == [True]

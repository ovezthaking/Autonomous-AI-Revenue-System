from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.integration


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

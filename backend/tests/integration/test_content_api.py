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


def test_run_content_returns_202(client, no_celery_broker):
    response = client.post("/content/run", json={"limit": 3})

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "generate_content"
    assert body["status"] == "queued"
    assert no_celery_broker == [("content.generate", [body["id"]])]


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
    assert no_celery_broker == [("content.publish_due", [])]


def test_reject_and_schedule_content(client, make_content_item):
    import uuid

    draft = make_content_item(status="draft")
    rejected = client.post(
        f"/content/{draft.id}/reject", json={"comment": "weak"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    # 404 when scheduling missing item (line 86)
    assert client.post(f"/content/{uuid.uuid4()}/schedule").status_code == 404

    # Schedule approved item -> 200 and status=scheduled (lines 94-102)
    approved = make_content_item(status="approved")
    scheduled = client.post(f"/content/{approved.id}/schedule", json={})
    assert scheduled.status_code == 200
    assert scheduled.json()["status"] == "scheduled"
    assert scheduled.json()["scheduled_for"] is not None


def test_publications_endpoints(
    client, db_session, make_content_item, no_celery_broker, monkeypatch
):
    import uuid

    from revenue_swarm.enums import PublicationStatus
    from revenue_swarm.models.publication import Publication

    item = make_content_item(status="scheduled")
    pub_review = Publication(
        content_item_id=item.id,
        target="wordpress",
        status=PublicationStatus.NEEDS_REVIEW.value,
    )
    pub_ok = Publication(
        content_item_id=item.id,
        target="html",
        status=PublicationStatus.SUCCEEDED.value,
        external_id="ext-1",
    )
    db_session.add_all([pub_review, pub_ok])
    db_session.commit()

    # 1. GET /publications (all and filtered by status)
    all_pubs = client.get("/publications")
    assert all_pubs.status_code == 200
    assert len(all_pubs.json()) == 2

    filtered = client.get(
        "/publications", params={"status": "needs_review", "limit": 10}
    )
    assert filtered.status_code == 200
    assert [p["id"] for p in filtered.json()] == [str(pub_review.id)]

    # 2. GET /publications/needs-review
    needs_rev = client.get("/publications/needs-review")
    assert needs_rev.status_code == 200
    assert [p["id"] for p in needs_rev.json()] == [str(pub_review.id)]

    # 3. GET /publications/meta
    monkeypatch.setenv("PUBLISH_ENABLED", "1")
    meta = client.get("/publications/meta")
    assert meta.status_code == 200
    assert meta.json() == {"publish_enabled": True}

    # 4. POST /publications/{id}/resolve branches
    assert (
        client.post(
            f"/publications/{uuid.uuid4()}/resolve",
            json={"resolution": "not_published"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/publications/{pub_ok.id}/resolve",
            json={"resolution": "not_published"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/publications/{pub_review.id}/resolve",
            json={"resolution": "published"},
        ).status_code
        == 422
    )

    res_pub = client.post(
        f"/publications/{pub_review.id}/resolve",
        json={
            "resolution": "published",
            "external_id": "wp-42",
            "external_url": "https://blog.test/p/42",
        },
    )
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "succeeded"
    db_session.refresh(item)
    assert item.status == "published"

    # Reset to needs_review and resolve as not_published
    pub_review.status = PublicationStatus.NEEDS_REVIEW.value
    db_session.commit()
    res_fail = client.post(
        f"/publications/{pub_review.id}/resolve",
        json={"resolution": "not_published"},
    )
    assert res_fail.status_code == 200
    assert res_fail.json()["status"] == "failed"
    db_session.refresh(pub_review)
    assert (pub_review.payload or {}).get("retryable") is True

    # 5. POST /publications/{id}/retract
    res_retract = client.post(f"/publications/{pub_ok.id}/retract")
    assert res_retract.status_code == 202
    assert ("content.retract", [str(pub_ok.id)]) in no_celery_broker

import pytest
from revenue_swarm.models.ebook_chapter import EbookChapter
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName

pytestmark = pytest.mark.integration


def _product(db, status="draft", slug="guide", extras=None) -> Product:
    row = Product(
        slug=slug,
        title="Guide",
        price_cents=1900,
        status=status,
        extras=extras,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_list_products_filters_by_status(client, db_session):
    _product(db_session, status="draft", slug="a")
    _product(db_session, status="live", slug="b")

    response = client.get("/products", params={"status": "live"})

    assert response.status_code == 200
    assert [row["slug"] for row in response.json()] == ["b"]


def test_propose_queues_the_task(client, no_celery_broker):
    response = client.post("/products/propose", json={"niche": "crm"})

    assert response.status_code == 202
    assert no_celery_broker == [(TaskName.EBOOK_PROPOSE, ["crm"])]


def test_chapters_are_listed_in_position_order(client, db_session):
    product = _product(db_session, status="outlined")
    for position in (2, 1):
        db_session.add(
            EbookChapter(
                product_id=product.id,
                position=position,
                title=f"Ch {position}",
                brief="brief",
            )
        )
    db_session.commit()

    response = client.get(f"/products/{product.id}/chapters")

    assert response.status_code == 200
    assert [row["position"] for row in response.json()] == [1, 2]


def test_approve_draft_twice_is_409_and_queues_once(
    client, db_session, no_celery_broker
):
    product = _product(db_session)

    first = client.post(f"/products/{product.id}/approve")
    second = client.post(f"/products/{product.id}/approve")

    assert first.status_code == 200
    assert first.json()["status"] == "outlining"
    assert second.status_code == 409
    assert len(no_celery_broker) == 1


def test_review_then_approve_goes_live(client, db_session):
    product = _product(db_session, status="assembled")

    blocked = client.post(f"/products/{product.id}/approve")
    review = client.post(
        f"/products/{product.id}/review", json={"reviewer": "ovezo"}
    )
    live = client.post(f"/products/{product.id}/approve")

    assert blocked.status_code == 409
    assert review.status_code == 200
    assert review.json()["extras"]["reviewed_by"] == "ovezo"
    assert live.json()["status"] == "live"


def test_review_is_only_allowed_on_assembled(client, db_session):
    product = _product(db_session, status="draft")

    response = client.post(
        f"/products/{product.id}/review", json={"reviewer": "ovezo"}
    )

    assert response.status_code == 409


def test_retry_chapters_only_while_writing(
    client, db_session, no_celery_broker
):
    writing = _product(db_session, status="writing", slug="w")
    draft = _product(db_session, status="draft", slug="d")

    ok = client.post(f"/products/{writing.id}/retry-chapters")
    refused = client.post(f"/products/{draft.id}/retry-chapters")

    assert ok.status_code == 202
    assert refused.status_code == 409
    assert len(no_celery_broker) == 1


def test_unknown_product_is_404(client):
    response = client.get("/products/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404

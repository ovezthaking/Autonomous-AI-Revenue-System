"""Integration tests for shop and ideas HITL endpoints."""

import uuid

import pytest
from app.services.discord_interactions import handle_interaction
from revenue_swarm.enums import (
    IdeaStatus,
    ListingStatus,
    OrderStatus,
    ProductKind,
)
from revenue_swarm.fulfillment import create_grant
from revenue_swarm.models.order import Order
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.product_listing import ProductListing
from revenue_swarm.tasks import TaskName

pytestmark = pytest.mark.integration


def test_ideas_and_listings_hitl_api_and_discord_buttons(
    client, db_session, no_celery_broker, monkeypatch
):
    monkeypatch.setattr("app.services.hitl.SHOP_ENABLED", True)

    idea = ProductIdea(
        term="budget planner printable",
        title="Budget Planner",
        kind=ProductKind.PRINTABLE.value,
        score=0.82,
        score_breakdown={
            "own_fit": 0.35,
            "demand": 0.22,
            "producibility": 0.25,
        },
        status=IdeaStatus.PROPOSED.value,
    )
    blocked_idea = ProductIdea(
        term="Taylor Swift planner",
        title="Taylor Swift planner",
        kind=ProductKind.PRINTABLE.value,
        score=0.0,
        score_breakdown={},
        status=IdeaStatus.BLOCKED.value,
        blocked_reason="denylist",
    )
    db_session.add_all([idea, blocked_idea])
    db_session.commit()

    # 1. GET /ideas?status=proposed and ?status=blocked
    resp_prop = client.get("/ideas?status=proposed")
    assert resp_prop.status_code == 200
    assert [i["id"] for i in resp_prop.json()] == [str(idea.id)]

    resp_blk = client.get("/ideas?status=blocked")
    assert resp_blk.status_code == 200
    assert [i["id"] for i in resp_blk.json()] == [str(blocked_idea.id)]

    # 2. Approve idea via Discord button -> queues shop.build
    res_btn = handle_interaction(
        db_session,
        {
            "type": 3,
            "member": {"user": {"id": "u_admin"}},
            "data": {"custom_id": f"product_idea:{idea.id}:approve"},
        },
        allowed=frozenset({"u_admin"}),
        dashboard_url="http://localhost:3000",
    )
    assert res_btn["type"] == 7
    assert (TaskName.SHOP_BUILD.value, [str(idea.id)]) in no_celery_broker

    # 3. Create draft listing and approve via POST /listings/{id}/approve
    product = Product(
        slug=f"rs-{uuid.uuid4().hex[:12]}",
        title="Budget Planner",
        kind=ProductKind.PRINTABLE.value,
        price_cents=900,
    )
    db_session.add(product)
    db_session.flush()
    listing = ProductListing(
        product_id=product.id,
        platform="shopify",
        handle=f"rs-{product.id.hex[:12]}",
        status=ListingStatus.DRAFT.value,
    )
    db_session.add(listing)
    db_session.commit()

    resp_list = client.get("/listings")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    resp_app = client.post(f"/listings/{listing.id}/approve")
    assert resp_app.status_code == 200
    assert (
        TaskName.SHOP_ACTIVATE.value,
        [str(listing.id)],
    ) in no_celery_broker


def test_download_endpoint_supports_a4_and_letter_formats(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        "app.api.downloads._too_fast", lambda key, limit=10: False
    )
    presigned_keys: list[str] = []

    def _fake_presigned(key: str, expires_in: int = 300) -> str:
        presigned_keys.append(key)
        return f"http://localhost:9000/bucket/{key}"

    monkeypatch.setattr(
        "app.api.downloads.storage.presigned_url", _fake_presigned
    )

    product = Product(
        slug="printable-dual",
        title="Dual Printable",
        kind=ProductKind.PRINTABLE.value,
        price_cents=900,
        asset_pdf="printables/printable-dual-a4.pdf",
        extras={"letter_pdf": "printables/printable-dual-letter.pdf"},
    )
    db_session.add(product)
    db_session.flush()
    order = Order(
        product_id=product.id,
        provider="shopify",
        provider_session_id="gid://shopify/Order/1:gid://shopify/LineItem/1",
        email="buyer@example.com",
        amount_cents=900,
        currency="USD",
        status=OrderStatus.FULFILLED.value,
    )
    db_session.add(order)
    db_session.commit()

    token, _ = create_grant(db_session, order)

    verify_resp = client.get(f"/download/{token}")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["formats"] == ["a4", "letter"]

    a4_resp = client.post(
        f"/download/{token}?format=a4",
        headers={"Accept": "application/json"},
    )
    assert a4_resp.status_code == 200
    assert a4_resp.json()["url"].endswith("printable-dual-a4.pdf")

    letter_resp = client.post(
        f"/download/{token}?format=letter",
        headers={"Accept": "application/json"},
    )
    assert letter_resp.status_code == 200
    assert letter_resp.json()["url"].endswith("printable-dual-letter.pdf")

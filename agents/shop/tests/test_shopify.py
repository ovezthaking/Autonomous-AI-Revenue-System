"""Shopify auth, GraphQL, listings, webhooks, and refunds."""

import base64
import hashlib
import hmac
import json
import uuid
from contextlib import contextmanager

import httpx
import pytest
from revenue_swarm import config
from revenue_swarm.enums import ListingStatus, OrderStatus, ProductStatus
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.models.product import Product
from revenue_swarm.models.product_listing import ProductListing
from shop_agent.listing import handle_for, save_listing
from shop_agent.platforms.fake import FakeShopPlatform
from shop_agent.platforms.shopify import ShopifyPlatform
from shop_agent.redaction import (
    PermanentError,
    TransientError,
    UnknownOutcomeError,
)
from shop_agent.shopify import auth as shopify_auth
from shop_agent.shopify.graphql import execute, mutation_result
from shop_agent.tasks import (
    shop_fulfill_task,
    shop_refund_task,
    sync_ebooks_task,
)
from sqlalchemy import func, select


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, tuple[str, int]] = {}
        self.locks_entered: int = 0

    def get(self, key: str) -> bytes | None:
        item = self.store.get(key)
        return item[0].encode("utf-8") if item else None

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = (value, ttl)

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    @contextmanager
    def lock(self, name: str, timeout: int = 30):
        self.locks_entered += 1
        yield


def _product() -> Product:
    return Product(
        id=uuid.uuid4(),
        slug=f"ebook-{uuid.uuid4().hex[:8]}",
        title="Automation Guide",
        description="Complete guide",
        kind="ebook",
        price_cents=1900,
        currency="USD",
        status=ProductStatus.LIVE.value,
    )


def _draft_listing(db) -> ProductListing:
    product = _product()
    db.add(product)
    db.commit()
    shop = FakeShopPlatform()
    res = shop.upsert_listing(product, ListingStatus.DRAFT)
    return save_listing(db, product, res)


def _hmac(body: bytes) -> str:
    digest = hmac.new(
        config.SHOPIFY_CLIENT_SECRET.encode(), body, hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def _paid_order(
    variant_gid: str,
    *,
    order_gid: str = "gid://shopify/Order/101",
    line_gid: str = "gid://shopify/LineItem/201",
    price: str = "19.00",
) -> bytes:
    return json.dumps(
        {
            "admin_graphql_api_id": order_gid,
            "email": "buyer@example.com",
            "currency": "USD",
            "line_items": [
                {
                    "admin_graphql_api_id": line_gid,
                    "admin_graphql_api_variant_id": variant_gid,
                    "price": price,
                    "quantity": 1,
                }
            ],
        }
    ).encode("utf-8")


def test_access_token_caches_with_early_expiry_and_lock(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(shopify_auth, "redis_client", fake_redis)
    calls: list[str] = []

    def _fake_post(url: str, data: dict, timeout: float):
        calls.append(url)
        return httpx.Response(
            200,
            json={"access_token": "shpat_live_1", "expires_in": 86400},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("shop_agent.shopify.auth.httpx.post", _fake_post)

    first = shopify_auth.access_token()
    second = shopify_auth.access_token()

    assert first == "shpat_live_1"
    assert second == "shpat_live_1"
    assert len(calls) == 1
    assert fake_redis.locks_entered == 1
    assert fake_redis.store[shopify_auth.TOKEN_KEY] == (
        "shpat_live_1",
        86400 - 600,
    )


def test_graphql_retries_once_on_401(monkeypatch):
    tokens = ["expired_tok", "fresh_tok"]
    invalidated: list[bool] = []
    sent_tokens: list[str] = []

    monkeypatch.setattr(
        "shop_agent.shopify.graphql.access_token", lambda: tokens.pop(0)
    )
    monkeypatch.setattr(
        "shop_agent.shopify.graphql.invalidate_token",
        lambda: invalidated.append(True),
    )

    def _fake_post(url: str, json: dict, headers: dict, timeout: float):
        tok = headers["X-Shopify-Access-Token"]
        sent_tokens.append(tok)
        if tok == "expired_tok":
            return httpx.Response(401, json={"errors": "Unauthorized"})
        return httpx.Response(200, json={"data": {"shop": {"name": "ok"}}})

    monkeypatch.setattr("shop_agent.shopify.graphql.httpx.post", _fake_post)

    data = execute("query { shop { name } }", {})
    assert data == {"shop": {"name": "ok"}}
    assert invalidated == [True]
    assert sent_tokens == ["expired_tok", "fresh_tok"]


def test_graphql_errors_and_throttling(monkeypatch):
    monkeypatch.setattr(
        "shop_agent.shopify.graphql.access_token", lambda: "tok"
    )

    def _throttled(*a, **k):
        return httpx.Response(
            200,
            json={
                "errors": [
                    {
                        "message": "Throttled",
                        "extensions": {"code": "THROTTLED"},
                    }
                ]
            },
        )

    monkeypatch.setattr("shop_agent.shopify.graphql.httpx.post", _throttled)
    with pytest.raises(TransientError):
        execute("query { shop { name } }", {})

    def _top_error(*a, **k):
        msg = f"Invalid field {config.SHOPIFY_CLIENT_SECRET}"
        return httpx.Response(
            200,
            json={"errors": [{"message": msg}]},
        )

    monkeypatch.setattr("shop_agent.shopify.graphql.httpx.post", _top_error)
    with pytest.raises(PermanentError) as exc_info:
        execute("query { shop { name } }", {})
    assert config.SHOPIFY_CLIENT_SECRET not in str(exc_info.value)

    def _timeout(*a, **k):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("shop_agent.shopify.graphql.httpx.post", _timeout)
    with pytest.raises(UnknownOutcomeError):
        execute("mutation { x }", {})


def test_user_errors_are_permanent():
    body = {"data": {"productSet": {"userErrors": [{"message": "bad"}]}}}
    with pytest.raises(PermanentError):
        mutation_result(body["data"], "productSet")


def test_handle_is_stable():
    product = Product(id=uuid.UUID(int=1), title="Guide", price_cents=1900)
    assert handle_for(product) == handle_for(product)
    assert handle_for(product).startswith("rs-")


def test_fake_upsert_does_not_duplicate():
    shop = FakeShopPlatform()
    product = _product()
    first = shop.upsert_listing(product, ListingStatus.DRAFT)
    second = shop.upsert_listing(product, ListingStatus.DRAFT)
    assert first.external_id == second.external_id
    assert len(shop.products) == 1
    stored = shop.products[handle_for(product)]
    assert stored["requiresShipping"] is False
    assert stored["tracked"] is False
    assert stored["status"] == "draft"


def test_shopify_product_set_payload_and_fulfilled_idempotency(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _fake_execute(query: str, variables: dict) -> dict:
        calls.append((query, variables))
        if "productSet" in query:
            return {
                "productSet": {
                    "product": {
                        "id": "gid://shopify/Product/99",
                        "handle": variables["identifier"]["handle"],
                        "status": "DRAFT",
                        "variants": {
                            "nodes": [
                                {"id": "gid://shopify/ProductVariant/88"}
                            ]
                        },
                    },
                    "userErrors": [],
                }
            }
        if "fulfillmentOrders" in query:
            return {
                "order": {
                    "fulfillmentOrders": {
                        "nodes": [
                            {
                                "id": "gid://shopify/FulfillmentOrder/1",
                                "status": "CLOSED",
                            },
                            {
                                "id": "gid://shopify/FulfillmentOrder/2",
                                "status": "OPEN",
                            },
                        ]
                    }
                }
            }
        return {
            "fulfillmentCreate": {
                "fulfillment": {
                    "id": "gid://shopify/Fulfillment/1",
                    "status": "SUCCESS",
                },
                "userErrors": [],
            }
        }

    monkeypatch.setattr("shop_agent.platforms.shopify.execute", _fake_execute)
    shop = ShopifyPlatform()
    prod = _product()
    res = shop.upsert_listing(prod, ListingStatus.DRAFT)
    assert res.external_id == "gid://shopify/Product/99"
    assert res.external_variant_id == "gid://shopify/ProductVariant/88"

    _, sent_vars = calls[0]
    inp = sent_vars["input"]
    assert inp["status"] == "DRAFT"
    variant = inp["variants"][0]
    assert variant["inventoryItem"]["requiresShipping"] is False
    assert variant["inventoryItem"]["tracked"] is False

    shop.mark_fulfilled("gid://shopify/Order/10")
    # Only the OPEN fulfillmentOrder (#2) should trigger fulfillmentCreate
    assert len(calls) == 3
    _, f_vars = calls[2]
    assert f_vars["fulfillment"]["notifyCustomer"] is False
    assert f_vars["fulfillment"]["lineItemsByFulfillmentOrder"] == [
        {"fulfillmentOrderId": "gid://shopify/FulfillmentOrder/2"}
    ]


def test_mark_fulfilled_does_not_notify():
    shop = FakeShopPlatform()
    shop.mark_fulfilled("gid://shopify/Order/1")
    assert shop.fulfilled[0]["notifyCustomer"] is False


@pytest.mark.integration
def test_duplicate_webhook_fulfills_once(client, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "revenue_swarm.fulfillment.send_delivery_email",
        lambda order, token: sent.append(token),
    )
    listing = _draft_listing(db)
    assert listing.external_variant_id is not None
    body = _paid_order(listing.external_variant_id)
    header = _hmac(body)
    first = client.post(
        "/webhooks/shopify",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": header,
            "X-Shopify-Webhook-Id": "wh_1",
            "X-Shopify-Topic": "orders/paid",
        },
    )
    second = client.post(
        "/webhooks/shopify",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": header,
            "X-Shopify-Webhook-Id": "wh_1",
            "X-Shopify-Topic": "orders/paid",
        },
    )
    shop_fulfill_task("wh_1")
    shop_fulfill_task("wh_1")
    assert first.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert len(sent) == 1


@pytest.mark.integration
def test_bad_hmac_writes_nothing(client, db):
    response = client.post(
        "/webhooks/shopify",
        content=b"{}",
        headers={"X-Shopify-Hmac-Sha256": "nope"},
    )
    assert response.status_code == 401
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


@pytest.mark.integration
def test_multi_item_order_and_unknown_variant_skipped(client, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "revenue_swarm.fulfillment.send_delivery_email",
        lambda order, token: sent.append((order.product_id, token)),
    )
    l1 = _draft_listing(db)
    l2 = _draft_listing(db)
    body = json.dumps(
        {
            "admin_graphql_api_id": "gid://shopify/Order/555",
            "email": "multi@example.com",
            "currency": "USD",
            "line_items": [
                {
                    "admin_graphql_api_id": "gid://shopify/LineItem/1",
                    "admin_graphql_api_variant_id": l1.external_variant_id,
                    "price": "15.00",
                    "total_discount": "3.00",
                    "quantity": 1,
                },
                {
                    "admin_graphql_api_id": "gid://shopify/LineItem/2",
                    "admin_graphql_api_variant_id": "gid://shopify/ProductVariant/unknown",
                    "price": "99.00",
                    "quantity": 1,
                },
                {
                    "admin_graphql_api_id": "gid://shopify/LineItem/3",
                    "admin_graphql_api_variant_id": l2.external_variant_id,
                    "price": "19.00",
                    "quantity": 1,
                },
            ],
        }
    ).encode("utf-8")
    resp = client.post(
        "/webhooks/shopify",
        content=body,
        headers={
            "X-Shopify-Hmac-Sha256": _hmac(body),
            "X-Shopify-Webhook-Id": "wh_multi",
            "X-Shopify-Topic": "orders/paid",
        },
    )
    assert resp.status_code == 200
    res = shop_fulfill_task("wh_multi")
    assert res == {"delivered": 2}
    orders = list(db.scalars(select(Order).order_by(Order.amount_cents)).all())
    assert len(orders) == 2
    assert orders[0].amount_cents == 1200  # 15.00 - 3.00 discount
    assert orders[1].amount_cents == 1900
    assert len(sent) == 2


@pytest.mark.integration
def test_refund_revokes_grant_and_empty_gid_never_revokes_all(
    client, db, monkeypatch
):
    monkeypatch.setattr(
        "revenue_swarm.fulfillment.send_delivery_email",
        lambda order, token: None,
    )
    l1 = _draft_listing(db)
    l2 = _draft_listing(db)
    assert l1.external_variant_id and l2.external_variant_id

    b1 = _paid_order(
        l1.external_variant_id,
        order_gid="gid://shopify/Order/700",
        line_gid="gid://shopify/LineItem/1",
    )
    b2 = _paid_order(
        l2.external_variant_id,
        order_gid="gid://shopify/Order/800",
        line_gid="gid://shopify/LineItem/2",
    )
    for idx, payload in enumerate((b1, b2), start=1):
        client.post(
            "/webhooks/shopify",
            content=payload,
            headers={
                "X-Shopify-Hmac-Sha256": _hmac(payload),
                "X-Shopify-Webhook-Id": f"wh_paid_{idx}",
                "X-Shopify-Topic": "orders/paid",
            },
        )
        shop_fulfill_task(f"wh_paid_{idx}")

    # 1. Refund with missing order_id / non-Order GID must NOT revoke anything
    bad_refund = json.dumps(
        {"admin_graphql_api_id": "gid://shopify/Refund/999"}
    ).encode("utf-8")
    client.post(
        "/webhooks/shopify",
        content=bad_refund,
        headers={
            "X-Shopify-Hmac-Sha256": _hmac(bad_refund),
            "X-Shopify-Webhook-Id": "wh_ref_bad",
            "X-Shopify-Topic": "refunds/create",
        },
    )
    assert shop_refund_task("wh_ref_bad") == {"refunded": 0}

    # 2. Valid refund for Order 700 revokes only Order 700's grant
    good_refund = json.dumps({"order_id": 700}).encode("utf-8")
    client.post(
        "/webhooks/shopify",
        content=good_refund,
        headers={
            "X-Shopify-Hmac-Sha256": _hmac(good_refund),
            "X-Shopify-Webhook-Id": "wh_ref_good",
            "X-Shopify-Topic": "refunds/create",
        },
    )
    assert shop_refund_task("wh_ref_good") == {"refunded": 1}

    o700 = db.scalar(
        select(Order).where(
            Order.provider_session_id.startswith("gid://shopify/Order/700:")
        )
    )
    o800 = db.scalar(
        select(Order).where(
            Order.provider_session_id.startswith("gid://shopify/Order/800:")
        )
    )
    assert o700 is not None and o700.status == OrderStatus.REFUNDED.value
    assert o800 is not None and o800.status == OrderStatus.FULFILLED.value
    g700 = db.scalar(
        select(DownloadGrant).where(DownloadGrant.order_id == o700.id)
    )
    g800 = db.scalar(
        select(DownloadGrant).where(DownloadGrant.order_id == o800.id)
    )
    assert g700 is not None and g700.revoked is True
    assert g800 is not None and g800.revoked is False


@pytest.mark.integration
def test_sync_ebooks_skips_active_listings(db, monkeypatch):
    monkeypatch.setattr("shop_agent.tasks.SHOP_ENABLED", True)
    p1 = _product()
    p2 = _product()
    db.add_all([p1, p2])
    db.commit()

    # p1 is already ACTIVE in Shopify
    shop = FakeShopPlatform()
    res1 = shop.upsert_listing(p1, ListingStatus.ACTIVE)
    save_listing(db, p1, res1, status=ListingStatus.ACTIVE)

    out = sync_ebooks_task()
    assert out == {"listed": 1}

    l1 = db.scalar(
        select(ProductListing).where(ProductListing.product_id == p1.id)
    )
    l2 = db.scalar(
        select(ProductListing).where(ProductListing.product_id == p2.id)
    )
    assert l1 is not None and l1.status == ListingStatus.ACTIVE.value
    assert l2 is not None and l2.status == ListingStatus.DRAFT.value

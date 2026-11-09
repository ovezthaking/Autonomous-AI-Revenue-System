import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from revenue_swarm import config
from revenue_swarm.enums import OrderStatus, ProductStatus
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.models.product import Product
from revenue_swarm.payments.lemonsqueezy import LemonSqueezyProvider
from revenue_swarm.payments.stripe import (
    StripeProvider,
    compute_stripe_signature,
)
from sales_agent.tasks import create_grant, fulfill_task, refund_task
from sqlalchemy import func, select

pytestmark = pytest.mark.integration


class _UnclosableSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self) -> None:
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


@pytest.fixture(autouse=True)
def _bind_worker_session_and_disable_ratelimit(db_session, monkeypatch):
    """Share the transactional db_session with sales_agent tasks in tests."""
    proxy = _UnclosableSessionProxy(db_session)
    monkeypatch.setattr("sales_agent.tasks.SessionLocal", lambda: proxy)
    monkeypatch.setattr("app.api.checkout._too_fast", lambda *a, **k: False)
    monkeypatch.setattr("app.api.downloads._too_fast", lambda *a, **k: False)


def _live_product(db, slug: str = "guide", price_cents: int = 1900) -> Product:
    product = Product(
        slug=slug,
        title="Guide to AI Agents",
        price_cents=price_cents,
        currency="USD",
        status=ProductStatus.LIVE.value,
        asset_pdf=f"ebooks/{slug}.pdf",
        asset_epub=f"ebooks/{slug}.epub",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _pending_order(
    db,
    product: Product,
    session_id: str = "fake_guide",
    provider: str = "fake",
) -> Order:
    order = Order(
        product_id=product.id,
        provider=provider,
        provider_session_id=session_id,
        amount_cents=product.price_cents,
        currency=product.currency,
        status=OrderStatus.PENDING.value,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _fake_sig() -> dict[str, str]:
    return {"x-fake-signature": config.FAKE_WEBHOOK_SECRET}


def test_duplicate_webhook_fulfills_once(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.api.webhooks.celery_app.send_task", lambda *a, **k: None
    )
    sent: list[str] = []
    monkeypatch.setattr(
        "sales_agent.tasks.send_delivery_email",
        lambda order, token: sent.append(token),
    )
    product = _live_product(db_session)
    _pending_order(db_session, product, session_id="fake_guide")

    body = json.dumps(
        {
            "id": "evt_1",
            "type": "payment_succeeded",
            "session_id": "fake_guide",
            "amount_cents": 1900,
            "email": "buyer@example.com",
        }
    ).encode()

    first = client.post(
        "/webhooks/payments", content=body, headers=_fake_sig()
    )
    second = client.post(
        "/webhooks/payments", content=body, headers=_fake_sig()
    )
    res1 = fulfill_task("evt_1")
    res2 = fulfill_task("evt_1")

    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert res1["status"] == "fulfilled"
    assert res2["status"] == "already_fulfilled"
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1
    assert (
        db_session.scalar(select(func.count()).select_from(DownloadGrant)) == 1
    )
    assert len(sent) == 1


def test_bad_signature_changes_nothing(client, db_session):
    response = client.post(
        "/webhooks/payments",
        content=b"{}",
        headers={"x-fake-signature": "wrong-secret"},
    )

    assert response.status_code == 400
    assert (
        db_session.scalar(select(func.count()).select_from(PaymentEvent)) == 0
    )


def test_unknown_webhook_event_type_returns_200_ignored(client, db_session):
    body = json.dumps(
        {"id": "evt_unknown", "type": "customer.updated"}
    ).encode()

    response = client.post(
        "/webhooks/payments", content=body, headers=_fake_sig()
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_amount_mismatch_flags_needs_review_and_does_not_fulfill(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        "app.api.webhooks.celery_app.send_task", lambda *a, **k: None
    )
    sent: list[str] = []
    monkeypatch.setattr(
        "sales_agent.tasks.send_delivery_email",
        lambda order, token: sent.append(token),
    )
    product = _live_product(db_session, price_cents=1900)
    order = _pending_order(db_session, product, session_id="fake_mismatch")

    body = json.dumps(
        {
            "id": "evt_mismatch",
            "type": "payment_succeeded",
            "session_id": "fake_mismatch",
            "amount_cents": 100,
        }
    ).encode()
    client.post("/webhooks/payments", content=body, headers=_fake_sig())
    result = fulfill_task("evt_mismatch")

    db_session.refresh(order)
    assert result == {"status": "needs_review"}
    assert order.status == OrderStatus.PENDING.value
    assert (order.extras or {}).get("needs_review") == "amount mismatch"
    assert sent == []


def test_net_subtotal_with_vat_fulfills_cleanly(db_session, monkeypatch):
    """Stripe Tax / MoR adds VAT to amount_total (e.g. 2337 cents),
    while amount_subtotal is 1900 cents. Must match against net subtotal."""
    sent: list[str] = []
    monkeypatch.setattr(
        "sales_agent.tasks.send_delivery_email",
        lambda order, token: sent.append(token),
    )
    product = _live_product(db_session, slug="vat-book", price_cents=1900)
    order = _pending_order(
        db_session, product, session_id="cs_test_vat_1", provider="stripe"
    )
    event = PaymentEvent(
        provider="stripe",
        event_id="evt_stripe_vat",
        event_type="payment_succeeded",
        payload={
            "id": "evt_stripe_vat",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_vat_1",
                    "payment_intent": "pi_vat_123",
                    "amount_subtotal": 1900,
                    "amount_total": 2337,  # +23% EU VAT
                    "currency": "usd",
                    "customer_details": {"email": "eu@example.com"},
                }
            },
        },
    )
    db_session.add(event)
    db_session.commit()

    result = fulfill_task("evt_stripe_vat")
    db_session.refresh(order)

    assert result == {"status": "fulfilled"}
    assert order.status == OrderStatus.FULFILLED.value
    assert order.provider_payment_id == "pi_vat_123"
    assert len(sent) == 1


def test_stripe_refund_matches_by_payment_intent_and_revokes_grant(
    db_session, monkeypatch
):
    """Stripe charge.refunded has payment_intent, not session_id."""
    monkeypatch.setattr(
        "sales_agent.tasks.send_delivery_email", lambda order, token: None
    )
    product = _live_product(db_session, slug="refund-book", price_cents=1900)
    order = _pending_order(
        db_session, product, session_id="cs_test_ref_1", provider="stripe"
    )
    pay_event = PaymentEvent(
        provider="stripe",
        event_id="evt_pay_1",
        event_type="payment_succeeded",
        payload={
            "id": "evt_pay_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_ref_1",
                    "payment_intent": "pi_stripe_999",
                    "amount_subtotal": 1900,
                    "amount_total": 1900,
                    "customer_details": {"email": "ref@example.com"},
                }
            },
        },
    )
    db_session.add(pay_event)
    db_session.commit()
    fulfill_task("evt_pay_1")

    ref_event = PaymentEvent(
        provider="stripe",
        event_id="evt_ref_1",
        event_type="refunded",
        payload={
            "id": "evt_ref_1",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_123",
                    "payment_intent": "pi_stripe_999",
                    "amount_refunded": 1900,
                }
            },
        },
    )
    db_session.add(ref_event)
    db_session.commit()

    ref_res = refund_task("evt_ref_1")
    db_session.refresh(order)
    grant = db_session.scalar(
        select(DownloadGrant).where(DownloadGrant.order_id == order.id)
    )

    assert ref_res == {"status": "refunded"}
    assert order.status == OrderStatus.REFUNDED.value
    assert grant is not None and grant.revoked is True


def test_stripe_real_hmac_signature_verification(monkeypatch):
    secret = "whsec_test_secret_123"
    monkeypatch.setattr(config, "PAYMENT_WEBHOOK_SECRET", secret)
    provider = StripeProvider()

    payload = json.dumps(
        {
            "id": "evt_sig_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_sig_1",
                    "payment_intent": "pi_sig_1",
                    "amount_subtotal": 1900,
                    "amount_total": 2100,
                    "currency": "usd",
                    "customer_details": {"email": "sig@example.com"},
                }
            },
        }
    ).encode()
    sig = compute_stripe_signature(payload, secret, timestamp=1700000000)
    note = provider.parse_webhook(payload, {"Stripe-Signature": sig})

    assert note.event_id == "evt_sig_1"
    assert note.event_type == "payment_succeeded"
    assert note.provider_session_id == "cs_sig_1"
    assert note.provider_payment_id == "pi_sig_1"
    assert note.amount_cents == 1900


def test_lemonsqueezy_custom_session_id_and_hmac(monkeypatch):
    secret = "ls_webhook_secret_456"
    monkeypatch.setattr(config, "PAYMENT_WEBHOOK_SECRET", secret)
    provider = LemonSqueezyProvider()

    payload = json.dumps(
        {
            "meta": {
                "event_name": "order_created",
                "event_id": "ls_evt_1",
                "custom_data": {"slug": "guide", "session_id": "ls_guide_abc"},
            },
            "data": {
                "id": "99999",
                "attributes": {
                    "order_number": 1001,
                    "user_email": "lemon@example.com",
                    "subtotal": 1900,
                    "total": 2337,
                    "currency": "USD",
                },
            },
        }
    ).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    note = provider.parse_webhook(payload, {"X-Signature": sig})

    assert note.event_id == "ls_evt_1"
    assert note.event_type == "payment_succeeded"
    assert note.provider_session_id == "ls_guide_abc"
    assert note.provider_payment_id == "1001"
    assert note.amount_cents == 1900


def test_checkout_ignores_a_client_price(client, db_session, monkeypatch):
    monkeypatch.setattr(config, "SALES_ENABLED", True)
    _live_product(db_session, slug="guide", price_cents=1900)

    response = client.post(
        "/checkout", json={"slug": "guide", "price_cents": 1}
    )
    order = db_session.scalar(select(Order))

    assert response.status_code == 200
    assert order is not None
    assert order.amount_cents == 1900


def test_checkout_rejects_non_live_product_and_disabled_sales(
    client, db_session, monkeypatch
):
    draft = Product(
        slug="draft-book", title="Draft", price_cents=1900, status="draft"
    )
    db_session.add(draft)
    db_session.commit()

    monkeypatch.setattr(config, "SALES_ENABLED", False)
    disabled_res = client.post("/checkout", json={"slug": "draft-book"})
    assert disabled_res.status_code == 503

    monkeypatch.setattr(config, "SALES_ENABLED", True)
    not_live_res = client.post("/checkout", json={"slug": "draft-book"})
    assert not_live_res.status_code == 404


def test_grant_column_has_no_plaintext_token(db_session):
    product = _live_product(db_session, slug="token-book")
    order = _pending_order(db_session, product, session_id="sess_tok")
    token, grant = create_grant(db_session, order)

    assert token not in grant.token_hash
    stored = db_session.scalar(
        select(DownloadGrant.token_hash).where(DownloadGrant.id == grant.id)
    )
    assert stored is not None
    assert token not in stored


def test_get_does_not_burn_downloads_and_post_consumes(
    client, db_session, monkeypatch
):
    """Email scanner GET requests must not consume downloads;
    POST consumes downloads and enforces expiry, exhaustion, and revocation."""
    monkeypatch.setattr(
        "revenue_swarm.storage.presigned_url",
        lambda key, expires_in=300: f"http://localhost:9000/signed/{key}",
    )
    product = _live_product(db_session, slug="dl-book")
    order = _pending_order(db_session, product, session_id="sess_dl")
    token, grant = create_grant(db_session, order)

    # 1. Three GET requests from email scanner do NOT increment downloads
    for _ in range(3):
        get_res = client.get(f"/download/{token}")
        assert get_res.status_code == 200
        assert get_res.json()["downloads_used"] == 0

    # 2. POST request consumes 1 download and redirects (302)
    post_res = client.post(f"/download/{token}", follow_redirects=False)
    assert post_res.status_code == 302
    assert (
        post_res.headers["location"]
        == "http://localhost:9000/signed/ebooks/dl-book.pdf"
    )
    db_session.refresh(grant)
    assert grant.downloads == 1

    # 3. Exhaust downloads -> 429
    grant.downloads = grant.max_downloads
    db_session.commit()
    assert client.get(f"/download/{token}").status_code == 429
    assert client.post(f"/download/{token}").status_code == 429

    # 4. Expired -> 410
    grant.downloads = 0
    grant.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()
    assert client.get(f"/download/{token}").status_code == 410
    assert client.post(f"/download/{token}").status_code == 410

    # 5. Revoked -> 404
    grant.expires_at = datetime.now(UTC) + timedelta(days=5)
    grant.revoked = True
    db_session.commit()
    assert client.get(f"/download/{token}").status_code == 404
    assert client.post(f"/download/{token}").status_code == 404

    # 6. Unknown token -> 404
    assert client.get("/download/nonexistent-token").status_code == 404


def test_orders_endpoints_do_not_expose_token_hash(client, db_session):
    product = _live_product(db_session, slug="ord-book")
    order = _pending_order(db_session, product, session_id="sess_ord_1")
    create_grant(db_session, order)

    list_res = client.get("/orders")
    assert list_res.status_code == 200
    rows = list_res.json()
    assert len(rows) == 1
    assert "token_hash" not in rows[0]

    by_sess = client.get("/orders/by-session/sess_ord_1")
    assert by_sess.status_code == 200
    assert by_sess.json()["status"] == "pending"


def test_stripe_live_mode_requires_sk_live_key(db_session, monkeypatch):
    monkeypatch.setattr(config, "PAYMENT_MODE", "live")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_123")
    product = _live_product(db_session, slug="live-guard")

    with pytest.raises(RuntimeError, match="live mode requires a live key"):
        StripeProvider().create_checkout(
            product, "http://localhost:3000/ok", "http://localhost:3000/cancel"
        )


def test_rate_limit_order_404_webhook_refund_and_download_edge_cases(
    client, db_session, no_celery_broker, monkeypatch
):
    from unittest.mock import MagicMock

    import app.api.checkout as checkout_api
    import app.api.downloads as downloads_api

    # 1. Test _too_fast directly on checkout and downloads
    # Restore real _too_fast functions (overridden by autouse fixture)
    monkeypatch.undo()

    fake_redis = MagicMock()
    fake_redis.incr.side_effect = [1, 15, 1, 15]
    monkeypatch.setattr(
        checkout_api.redis_lib, "from_url", lambda *_a, **_kw: fake_redis
    )
    monkeypatch.setattr(
        downloads_api.redis_lib, "from_url", lambda *_a, **_kw: fake_redis
    )
    assert checkout_api._too_fast("k1", limit=10) is False
    assert checkout_api._too_fast("k1", limit=10) is True
    assert downloads_api._too_fast("k2", limit=10) is False
    assert downloads_api._too_fast("k2", limit=10) is True
    assert fake_redis.expire.call_count == 2

    # Redis exception returns False
    monkeypatch.setattr(
        checkout_api.redis_lib,
        "from_url",
        MagicMock(side_effect=RuntimeError("redis down")),
    )
    monkeypatch.setattr(
        downloads_api.redis_lib,
        "from_url",
        MagicMock(side_effect=RuntimeError("redis down")),
    )
    assert checkout_api._too_fast("k1") is False
    assert downloads_api._too_fast("k2") is False

    # 2. 429 on /checkout, GET /download/{token}, and POST /download/{token}
    monkeypatch.setattr(config, "SALES_ENABLED", True)
    monkeypatch.setattr(checkout_api, "_too_fast", lambda *_a, **_kw: True)
    monkeypatch.setattr(downloads_api, "_too_fast", lambda *_a, **_kw: True)
    assert client.post("/checkout", json={"slug": "guide"}).status_code == 429
    assert client.get("/download/tok").status_code == 429
    assert client.post("/download/tok").status_code == 429
    monkeypatch.setattr(downloads_api, "_too_fast", lambda *_a, **_kw: False)

    # 3. GET /orders/by-session/{session_id} -> 404 (orders.py line 26)
    assert client.get("/orders/by-session/missing-session").status_code == 404

    # 4. POST /webhooks/payments with refunded event -> queues SALES_REFUND
    refund_body = json.dumps(
        {"id": "evt_ref_api", "type": "refunded", "session_id": "s1"}
    ).encode()
    ref_res = client.post(
        "/webhooks/payments", content=refund_body, headers=_fake_sig()
    )
    assert ref_res.status_code == 200
    assert ref_res.json() == {"status": "accepted"}

    # 5. _validate_grant edge cases: naive expires_at, missing order/asset_pdf
    product_no_pdf = Product(
        slug="no-pdf",
        title="No PDF",
        price_cents=1000,
        currency="USD",
        status=ProductStatus.LIVE.value,
        asset_pdf=None,
    )
    db_session.add(product_no_pdf)
    db_session.commit()
    order = _pending_order(
        db_session, product_no_pdf, session_id="sess_no_pdf"
    )
    token, _grant = create_grant(db_session, order)

    # Asset not found -> 404
    res_no_asset = client.get(f"/download/{token}")
    assert res_no_asset.status_code == 404
    assert res_no_asset.json()["detail"] == "Asset not found"

    # Naive expires_at and Order not found
    naive_grant = DownloadGrant(
        order_id=order.id,
        token_hash=downloads_api.sha256_hex("naive-tok"),
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_downloads=3,
        downloads=0,
        revoked=False,
    )
    orig_get = db_session.get

    def _fake_get(model, ident):
        if model is Order:
            return None
        return orig_get(model, ident)

    monkeypatch.setattr(db_session, "scalar", lambda _stmt: naive_grant)
    monkeypatch.setattr(db_session, "get", _fake_get)
    res_no_order = client.get("/download/naive-tok")
    assert res_no_order.status_code == 404
    assert res_no_order.json()["detail"] == "Order not found"

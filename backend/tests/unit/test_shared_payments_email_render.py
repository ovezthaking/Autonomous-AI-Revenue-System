"""Unit and integration tests for revenue_swarm payments, email, fulfillment,
render, db, and testing.fixtures."""

import hashlib
import hmac
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from revenue_swarm import config, db as db_mod, fulfillment, payments
from revenue_swarm.email.console import ConsoleEmail
from revenue_swarm.email.resend import ResendEmail, send_delivery_email
from revenue_swarm.enums import OrderStatus, ProductStatus
from revenue_swarm.models.order import Order
from revenue_swarm.models.product import Product
from revenue_swarm.payments.base import SignatureError, get_header
from revenue_swarm.payments.fake import FakeProvider
from revenue_swarm.payments.lemonsqueezy import LemonSqueezyProvider
from revenue_swarm.payments.stripe import (
    StripeProvider,
    _verify_stripe_signature,
    compute_stripe_signature,
)
from revenue_swarm.render import pdf as pdf_mod
from revenue_swarm.testing import fixtures as fixtures_mod


def test_payment_providers_factory_and_edge_cases(monkeypatch):
    # 1. get_payment_provider factory (payments/__init__.py lines 15, 17)
    monkeypatch.setattr(config, "PAYMENT_PROVIDER", "stripe")
    assert isinstance(payments.get_payment_provider(), StripeProvider)
    monkeypatch.setattr(config, "PAYMENT_PROVIDER", "lemonsqueezy")
    assert isinstance(payments.get_payment_provider(), LemonSqueezyProvider)

    # 2. get_header missing key (payments/base.py line 50)
    assert get_header({"X-Present": "1"}, "x-missing") == ""

    # 3. FakeProvider invalid JSON (payments/fake.py lines 36-37)
    with pytest.raises(SignatureError, match="invalid json body"):
        FakeProvider().parse_webhook(
            b"{bad", {"x-fake-signature": config.FAKE_WEBHOOK_SECRET}
        )

    # 4. LemonSqueezyProvider create_checkout & parse_webhook errors
    product = Product(
        id=uuid.uuid4(),
        slug="ebook-1",
        title="Ebook 1",
        price_cents=1900,
        currency="USD",
        provider_price_id="var_1",
        status=ProductStatus.LIVE.value,
    )
    fake_ls_resp = MagicMock()
    fake_ls_resp.json.return_value = {
        "data": {"attributes": {"url": "https://ls.test/checkout/1"}}
    }
    monkeypatch.setattr(
        "revenue_swarm.payments.lemonsqueezy.httpx.post",
        lambda *_a, **_kw: fake_ls_resp,
    )
    ls = LemonSqueezyProvider()
    sess = ls.create_checkout(product, "http://ok", "http://cancel")
    assert sess.url == "https://ls.test/checkout/1"
    assert sess.provider_session_id.startswith("ls_ebook-1_")

    monkeypatch.setattr(config, "PAYMENT_WEBHOOK_SECRET", "ls_sec")
    with pytest.raises(SignatureError, match="bad lemon signature"):
        ls.parse_webhook(b"{}", {})
    with pytest.raises(SignatureError, match="bad lemon signature"):
        ls.parse_webhook(b"{}", {"x-signature": "wrong"})

    bad_json = b"{not-json"
    valid_ls_sig = hmac.new(b"ls_sec", bad_json, hashlib.sha256).hexdigest()
    with pytest.raises(SignatureError, match="invalid lemon json"):
        ls.parse_webhook(bad_json, {"x-signature": valid_ls_sig})

    # 5. StripeProvider signature validation, checkout, and parse_webhook
    with pytest.raises(SignatureError, match="missing stripe signature"):
        _verify_stripe_signature(b"{}", "", "sec")
    with pytest.raises(SignatureError, match="malformed stripe signature"):
        _verify_stripe_signature(b"{}", "garbage,t=123", "sec")
    with pytest.raises(SignatureError, match="invalid stripe signature"):
        _verify_stripe_signature(b"{}", "garbage,t=123,v1=wrong", "sec")

    monkeypatch.setattr(config, "PAYMENT_MODE", "test")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_123")
    fake_stripe_resp = MagicMock()
    fake_stripe_resp.json.return_value = {
        "id": "cs_123",
        "url": "https://stripe.test/pay",
    }
    monkeypatch.setattr(
        "revenue_swarm.payments.stripe.httpx.post",
        lambda *_a, **_kw: fake_stripe_resp,
    )
    sp = StripeProvider()
    st_sess = sp.create_checkout(product, "http://ok", "http://cancel")
    assert st_sess.provider_session_id == "cs_123"

    monkeypatch.setattr(config, "PAYMENT_WEBHOOK_SECRET", "st_sec")
    st_bad_sig = compute_stripe_signature(bad_json, "st_sec")
    with pytest.raises(SignatureError, match="invalid stripe json"):
        sp.parse_webhook(bad_json, {"stripe-signature": st_bad_sig})

    refund_payload = json.dumps(
        {
            "id": "evt_ref_99",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_99",
                    "payment_intent": "pi_99",
                    "checkout_session": "cs_99",
                    "amount_total": 1900,
                    "receipt_email": "buyer@test.com",
                }
            },
        }
    ).encode()
    st_ref_sig = compute_stripe_signature(refund_payload, "st_sec")
    note = sp.parse_webhook(refund_payload, {"stripe-signature": st_ref_sig})
    assert note.event_type == "refunded"
    assert note.provider_session_id == "cs_99"
    assert note.provider_payment_id == "pi_99"


def test_email_console_and_resend(monkeypatch):
    ConsoleEmail().send("user@test.com", "Hello", "Body")

    fake_resp = MagicMock()
    called = []

    def _fake_post(url, **kwargs):
        called.append((url, kwargs))
        return fake_resp

    monkeypatch.setattr("revenue_swarm.email.resend.httpx.post", _fake_post)
    ResendEmail().send("user@test.com", "Subj", "Text")
    assert len(called) == 1

    order = Order(email="buyer@test.com")
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "resend")
    send_delivery_email(order, "tok_abcdef123456")
    assert len(called) == 2

    monkeypatch.setattr(config, "EMAIL_PROVIDER", "console")
    send_delivery_email(order, "tok_abcdef123456")


def test_render_pdf_and_validate_assets(tmp_path: Path, monkeypatch):
    import pypdf

    ran = []
    monkeypatch.setattr(
        pdf_mod.subprocess,
        "run",
        lambda cmd, **kw: ran.append((cmd, kw)),
    )
    out_pdf = tmp_path / "sub" / "book.pdf"
    pdf_mod.render_pdf("<h1>Title</h1>", "h1 { color: black; }", out_pdf)
    assert out_pdf.with_suffix(".html").exists()
    assert out_pdf.with_suffix(".css").exists()
    assert len(ran) == 1

    out_pdf.write_bytes(b"x" * 6000)
    fake_reader = MagicMock()
    fake_reader.pages = [object(), object()]
    monkeypatch.setattr(pypdf, "PdfReader", lambda _p: fake_reader)

    pdf_mod.validate_assets(out_pdf, page_count=2, min_bytes=5000)

    with pytest.raises(RuntimeError, match="pdf too small"):
        pdf_mod.validate_assets(out_pdf, page_count=5, min_bytes=5000)


def test_db_get_db_and_ensure_database_exists(monkeypatch):
    # 1. db.get_db generator (db.py lines 15-19)
    fake_sess = MagicMock()
    monkeypatch.setattr(db_mod, "SessionLocal", lambda: fake_sess)
    gen = db_mod.get_db()
    yielded = next(gen)
    assert yielded is fake_sess
    with pytest.raises(StopIteration):
        next(gen)
    fake_sess.close.assert_called_once()

    # 2. _ensure_database_exists when DB missing & DuplicateDatabase raised
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_cursor = MagicMock()
    fake_cursor.fetchone.return_value = None

    def _exec(query, *_a):
        if isinstance(query, str):
            return fake_cursor
        raise psycopg.errors.DuplicateDatabase("already exists")

    fake_conn.execute.side_effect = _exec
    monkeypatch.setattr(
        fixtures_mod.psycopg, "connect", lambda *_a, **_kw: fake_conn
    )
    fixtures_mod._ensure_database_exists(
        "postgresql+psycopg://u:p@localhost:5432/new_db"
    )


@pytest.mark.integration
def test_fulfill_order_and_nested_savepoint_restart(db_session, monkeypatch):
    monkeypatch.setattr(
        fulfillment, "send_delivery_email", lambda *_a, **_kw: None
    )
    # Trigger savepoint end on connection so _restart_savepoint hits line 115
    nested_tx = db_session.bind.get_nested_transaction()
    if nested_tx is not None:
        nested_tx.rollback()
    db_session.rollback()

    product = Product(
        slug="shared-fulfill-book",
        title="Fulfill Book",
        price_cents=1500,
        currency="USD",
        status=ProductStatus.LIVE.value,
    )
    db_session.add(product)
    db_session.commit()

    order = Order(
        product_id=product.id,
        provider="fake",
        provider_session_id="sess_fulfill_1",
        email="buyer@test.com",
        amount_cents=1500,
        currency="USD",
        status=OrderStatus.PENDING.value,
    )
    db_session.add(order)
    db_session.commit()

    assert fulfillment.fulfill_order(db_session, order) == 1
    assert fulfillment.fulfill_order(db_session, order) == 0

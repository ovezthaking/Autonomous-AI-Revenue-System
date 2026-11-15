import pytest
from revenue_swarm.enums import OrderStatus, ProductStatus
from revenue_swarm.models.download_grant import DownloadGrant
from revenue_swarm.models.order import Order
from revenue_swarm.models.payment_event import PaymentEvent
from revenue_swarm.models.product import Product
from sales_agent.tasks import fulfill_task, refund_task
from sqlalchemy import select

pytestmark = pytest.mark.integration


def test_fulfill_and_refund_lifecycle(db_session):
    product = Product(
        slug="sales-test-book",
        title="Sales Test Book",
        price_cents=2900,
        currency="USD",
        status=ProductStatus.LIVE.value,
        asset_pdf="ebooks/sales-test-book.pdf",
    )
    db_session.add(product)
    db_session.commit()

    order = Order(
        product_id=product.id,
        provider="stripe",
        provider_session_id="cs_test_lifecycle",
        amount_cents=2900,
        currency="USD",
        status=OrderStatus.PENDING.value,
    )
    db_session.add(order)
    db_session.commit()

    ev_paid = PaymentEvent(
        provider="stripe",
        event_id="evt_paid_lifecycle",
        event_type="checkout.session.completed",
        payload={
            "id": "evt_paid_lifecycle",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_lifecycle",
                    "payment_intent": "pi_lifecycle_1",
                    "amount_subtotal": 2900,
                    "amount_total": 3567,
                    "currency": "usd",
                    "customer_details": {"email": "reader@example.com"},
                }
            },
        },
    )
    db_session.add(ev_paid)
    db_session.commit()

    res = fulfill_task(ev_paid.event_id)
    assert res["status"] == "fulfilled"

    db_session.refresh(order)
    assert order.status == OrderStatus.FULFILLED.value
    assert order.provider_payment_id == "pi_lifecycle_1"
    assert order.email == "reader@example.com"

    grant = db_session.scalar(
        select(DownloadGrant).where(DownloadGrant.order_id == order.id)
    )
    assert grant is not None
    assert grant.revoked is False

    ev_refund = PaymentEvent(
        provider="stripe",
        event_id="evt_refund_lifecycle",
        event_type="charge.refunded",
        payload={
            "id": "evt_refund_lifecycle",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_lifecycle_1",
                    "payment_intent": "pi_lifecycle_1",
                    "amount_refunded": 3567,
                    "currency": "usd",
                }
            },
        },
    )
    db_session.add(ev_refund)
    db_session.commit()

    ref_res = refund_task(ev_refund.event_id)
    assert ref_res["status"] == "refunded"

    db_session.refresh(order)
    db_session.refresh(grant)
    assert order.status == OrderStatus.REFUNDED.value
    assert grant.revoked is True


def test_sales_helpers_and_edge_cases(db_session):
    import sales_agent.worker as worker_mod
    from sales_agent.tasks import (
        _amount_matches,
        _email_from,
        _order_for,
        _payment_id_from,
        _session_id_from,
    )

    assert worker_mod.celery_app is not None

    # 1. _session_id_from branches
    assert _session_id_from({"session_id": "fake_sess"}) == "fake_sess"
    assert (
        _session_id_from({"meta": {"custom_data": {"session_id": "ls_sess"}}})
        == "ls_sess"
    )
    assert (
        _session_id_from(
            {
                "type": "charge.refunded",
                "data": {"object": {"checkout_session": "cs_ref"}},
            }
        )
        == "cs_ref"
    )
    assert (
        _session_id_from(
            {"data": {"id": "ls_123", "attributes": {"total": 100}}}
        )
        == "ls_123"
    )
    assert _session_id_from({}) is None

    # 2. _payment_id_from branches
    assert _payment_id_from({"payment_id": "fake_pay"}) == "fake_pay"
    assert (
        _payment_id_from(
            {"type": "charge.refunded", "data": {"object": {"id": "ch_99"}}}
        )
        == "ch_99"
    )
    assert (
        _payment_id_from({"data": {"attributes": {"order_number": 456}}})
        == "456"
    )
    assert _payment_id_from({}) is None

    # 3. _email_from branches
    assert (
        _email_from(
            PaymentEvent(
                provider="f",
                event_id="e1",
                event_type="t",
                payload={"email": "a@b.c"},
            )
        )
        == "a@b.c"
    )
    assert (
        _email_from(
            PaymentEvent(
                provider="ls",
                event_id="e2",
                event_type="t",
                payload={"data": {"attributes": {"user_email": "ls@b.c"}}},
            )
        )
        == "ls@b.c"
    )
    assert (
        _email_from(
            PaymentEvent(
                provider="s", event_id="e3", event_type="t", payload={}
            )
        )
        is None
    )

    # 4. _amount_matches Lemon Squeezy branch
    dummy_order = Order(
        provider="ls",
        provider_session_id="s",
        amount_cents=1500,
        currency="USD",
    )
    ls_ev = PaymentEvent(
        provider="ls",
        event_id="e_ls",
        event_type="order_created",
        payload={"data": {"attributes": {"subtotal": 1500}}},
    )
    assert _amount_matches(dummy_order, ls_ev) is True

    # 5. Task edge cases: missing event/order, already fulfilled, mismatch
    assert fulfill_task("missing_evt") == {"status": "event_not_found"}
    assert refund_task("missing_evt") == {"status": "event_not_found"}

    ev_orphan = PaymentEvent(
        provider="fake",
        event_id="evt_orphan",
        event_type="paid",
        payload={"session_id": "no_such_session", "payment_id": "no_such_pay"},
    )
    db_session.add(ev_orphan)
    db_session.commit()
    assert _order_for(db_session, ev_orphan, lock=False) is None
    assert fulfill_task("evt_orphan") == {"status": "order_not_found"}
    assert refund_task("evt_orphan") == {"status": "order_not_found"}

    product = Product(
        slug="sales-edge-book",
        title="Edge Book",
        price_cents=2000,
        currency="USD",
        status=ProductStatus.LIVE.value,
    )
    db_session.add(product)
    db_session.commit()

    order = Order(
        product_id=product.id,
        provider="fake",
        provider_session_id="sess_edge",
        amount_cents=2000,
        currency="USD",
        status=OrderStatus.PENDING.value,
    )
    db_session.add(order)
    db_session.commit()

    ev_mismatch = PaymentEvent(
        provider="fake",
        event_id="evt_mismatch",
        event_type="paid",
        payload={"session_id": "sess_edge", "subtotal": 999},
    )
    db_session.add(ev_mismatch)
    db_session.commit()
    assert fulfill_task("evt_mismatch") == {"status": "needs_review"}
    db_session.refresh(order)
    assert order.extras == {"needs_review": "amount mismatch"}

    order.status = OrderStatus.FULFILLED.value
    db_session.commit()
    assert fulfill_task("evt_mismatch") == {"status": "already_fulfilled"}

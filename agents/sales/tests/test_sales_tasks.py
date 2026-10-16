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

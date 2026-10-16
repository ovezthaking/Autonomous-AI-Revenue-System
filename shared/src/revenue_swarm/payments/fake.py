import hmac
import json
import uuid
from collections.abc import Mapping

from revenue_swarm import config
from revenue_swarm.models.product import Product
from revenue_swarm.payments.base import (
    CheckoutSession,
    PaymentNotification,
    SignatureError,
    get_header,
)


class FakeProvider:
    name = "fake"

    def create_checkout(
        self, product: Product, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        session_id = f"fake_{product.slug}_{uuid.uuid4().hex[:8]}"
        return CheckoutSession(
            provider_session_id=session_id,
            url=f"{success_url}?session_id={session_id}",
        )

    def parse_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> PaymentNotification:
        sig = get_header(headers, "x-fake-signature")
        if not sig or not hmac.compare_digest(sig, config.FAKE_WEBHOOK_SECRET):
            raise SignatureError("bad fake signature")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SignatureError("invalid json body") from exc

        amount_cents = (
            data.get("subtotal")
            if data.get("subtotal") is not None
            else data.get("amount_cents")
        )
        return PaymentNotification(
            event_id=str(data["id"]),
            event_type=str(data.get("type", "ignored")),
            provider_session_id=data.get("session_id"),
            provider_payment_id=data.get("payment_id"),
            email=data.get("email"),
            amount_cents=amount_cents,
            currency=data.get("currency"),
            raw=data,
        )

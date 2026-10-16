import hashlib
import hmac
import json
from collections.abc import Mapping

import httpx

from revenue_swarm import config
from revenue_swarm.models.product import Product
from revenue_swarm.payments.base import (
    CheckoutSession,
    PaymentNotification,
    SignatureError,
    get_header,
)


def compute_stripe_signature(
    payload: bytes, secret: str, timestamp: int = 1700000000
) -> str:
    """Build a standard Stripe-Signature header value (`t=...,v1=...`)."""
    signed_payload = f"{timestamp}.".encode() + payload
    digest = hmac.new(
        secret.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def _verify_stripe_signature(
    payload: bytes, sig_header: str, secret: str
) -> None:
    if not sig_header or not secret:
        raise SignatureError("missing stripe signature or webhook secret")
    timestamp: str | None = None
    signatures: list[str] = []
    for item in sig_header.split(","):
        parts = item.strip().split("=", 1)
        if len(parts) != 2:
            continue
        k, v = parts
        if k == "t":
            timestamp = v
        elif k == "v1":
            signatures.append(v)

    if not timestamp or not signatures:
        raise SignatureError("malformed stripe signature header")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        secret.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise SignatureError("invalid stripe signature")


class StripeProvider:
    name = "stripe"

    def create_checkout(
        self, product: Product, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        if config.PAYMENT_MODE == "live" and not (
            config.STRIPE_SECRET_KEY.startswith("sk_live_")
        ):
            msg = "live mode requires a live key"
            raise RuntimeError(msg)

        response = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            headers={"Authorization": f"Bearer {config.STRIPE_SECRET_KEY}"},
            data={
                "mode": "payment",
                "line_items[0][price_data][currency]": (
                    product.currency.lower()
                ),
                "line_items[0][price_data][unit_amount]": str(
                    product.price_cents
                ),
                "line_items[0][price_data][product_data][name]": product.title,
                "line_items[0][quantity]": "1",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata[slug]": product.slug,
                "consent_collection[terms_of_service]": "required",
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return CheckoutSession(
            provider_session_id=str(data["id"]),
            url=str(data["url"]),
        )

    def parse_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> PaymentNotification:
        sig_header = get_header(headers, "stripe-signature")
        _verify_stripe_signature(
            body, sig_header, config.PAYMENT_WEBHOOK_SECRET
        )
        try:
            event = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SignatureError("invalid stripe json") from exc

        event_type = event.get("type", "")
        kind = {
            "checkout.session.completed": "payment_succeeded",
            "charge.refunded": "refunded",
        }.get(event_type, "ignored")

        obj = (event.get("data") or {}).get("object") or {}
        if event_type == "charge.refunded":
            # charge.refunded carries payment_intent, not session id
            session_id = obj.get("checkout_session")
            payment_id = obj.get("payment_intent") or obj.get("id")
        else:
            session_id = obj.get("id")
            payment_id = obj.get("payment_intent")

        # use net amount_subtotal before tax/VAT when available
        amount_cents = (
            obj.get("amount_subtotal")
            if obj.get("amount_subtotal") is not None
            else obj.get("amount_total")
        )
        email = (obj.get("customer_details") or {}).get("email") or obj.get(
            "receipt_email"
        )
        return PaymentNotification(
            event_id=str(event["id"]),
            event_type=kind,
            provider_session_id=str(session_id) if session_id else None,
            provider_payment_id=str(payment_id) if payment_id else None,
            email=email,
            amount_cents=amount_cents,
            currency=obj.get("currency"),
            raw=dict(event),
        )

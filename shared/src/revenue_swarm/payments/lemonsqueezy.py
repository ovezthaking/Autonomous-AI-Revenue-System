import hashlib
import hmac
import json
import uuid
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


class LemonSqueezyProvider:
    name = "lemonsqueezy"

    def create_checkout(
        self, product: Product, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        # bind custom session_id in checkout_data.custom so webhook
        # order_created can reliably correlate back to our pending Order.
        session_id = f"ls_{product.slug}_{uuid.uuid4().hex[:8]}"
        response = httpx.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers={"Authorization": f"Bearer {config.LEMONSQUEEZY_API_KEY}"},
            json={
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "product_options": {"redirect_url": success_url},
                        "checkout_data": {
                            "custom": {
                                "slug": product.slug,
                                "session_id": session_id,
                            }
                        },
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": config.LS_STORE_ID,
                            }
                        },
                        "variant": {
                            "data": {
                                "type": "variants",
                                "id": product.provider_price_id,
                            }
                        },
                    },
                }
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return CheckoutSession(
            provider_session_id=session_id,
            url=str(data["attributes"]["url"]),
        )

    def parse_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> PaymentNotification:
        sig = get_header(headers, "x-signature")
        if not sig or not config.PAYMENT_WEBHOOK_SECRET:
            raise SignatureError("bad lemon signature")
        digest = hmac.new(
            config.PAYMENT_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(digest, sig):
            raise SignatureError("bad lemon signature")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SignatureError("invalid lemon json") from exc

        meta = data.get("meta") or {}
        name = meta.get("event_name", "")
        kind = {
            "order_created": "payment_succeeded",
            "order_refunded": "refunded",
        }.get(name, "ignored")

        payload_data = data.get("data") or {}
        attrs = payload_data.get("attributes") or {}
        custom = meta.get("custom_data") or {}

        # prefer custom_data.session_id, fallback to data.id
        session_id = custom.get("session_id") or str(
            payload_data.get("id", "")
        )
        payment_id = str(
            attrs.get("order_number") or payload_data.get("id") or ""
        )

        # prefer net subtotal before VAT
        amount_cents = (
            attrs.get("subtotal")
            if attrs.get("subtotal") is not None
            else attrs.get("total")
        )
        return PaymentNotification(
            event_id=str(meta.get("event_id") or payload_data["id"]),
            event_type=kind,
            provider_session_id=session_id or None,
            provider_payment_id=payment_id or None,
            email=attrs.get("user_email"),
            amount_cents=amount_cents,
            currency=attrs.get("currency"),
            raw=data,
        )

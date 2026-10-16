from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from revenue_swarm.models.product import Product


@dataclass(frozen=True)
class CheckoutSession:
    provider_session_id: str
    url: str


@dataclass(frozen=True)
class PaymentNotification:
    """Normalized payment webhook payload independent of the provider."""

    event_id: str
    event_type: str  # payment_succeeded | refunded | ignored
    provider_session_id: str | None
    provider_payment_id: str | None
    email: str | None
    amount_cents: int | None
    currency: str | None
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    name: str

    def create_checkout(
        self, product: Product, success_url: str, cancel_url: str
    ) -> CheckoutSession: ...

    def parse_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> PaymentNotification: ...


class SignatureError(Exception):
    """Webhook signature does not match the raw body."""


def get_header(headers: Mapping[str, str], key: str) -> str:
    """Case-insensitive header lookup."""
    target = key.lower()
    for k, v in headers.items():
        if k.lower() == target:
            return v
    return ""

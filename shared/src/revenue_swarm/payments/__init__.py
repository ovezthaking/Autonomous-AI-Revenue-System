from revenue_swarm import config
from revenue_swarm.payments.base import (
    CheckoutSession,
    PaymentNotification,
    PaymentProvider,
    SignatureError,
)
from revenue_swarm.payments.fake import FakeProvider
from revenue_swarm.payments.lemonsqueezy import LemonSqueezyProvider
from revenue_swarm.payments.stripe import StripeProvider


def get_payment_provider() -> PaymentProvider:
    if config.PAYMENT_PROVIDER == "stripe":
        return StripeProvider()
    if config.PAYMENT_PROVIDER == "lemonsqueezy":
        return LemonSqueezyProvider()
    return FakeProvider()


__all__ = [
    "CheckoutSession",
    "FakeProvider",
    "LemonSqueezyProvider",
    "PaymentNotification",
    "PaymentProvider",
    "SignatureError",
    "StripeProvider",
    "get_payment_provider",
]

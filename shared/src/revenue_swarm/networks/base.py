from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

import httpx

from revenue_swarm.config import NETWORK_SECRETS
from revenue_swarm.models.affiliate_program import AffiliateProgram


@dataclass(frozen=True)
class TrackingLink:
    url: str
    network_link_id: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PerformanceRow:
    day: date
    program_id: str | None = None
    subid: str | None = None
    clicks: int = 0
    conversions_pending: int = 0
    conversions_approved: int = 0
    conversions_declined: int = 0
    revenue_pending_cents: int = 0
    revenue_approved_cents: int = 0
    currency: str = "USD"


class AffiliateNetwork(Protocol):
    name: str
    allow_redirect: bool

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink: ...

    def fetch_performance(
        self, since: date, until: date
    ) -> list[PerformanceRow]: ...


class PermanentNetworkError(Exception):
    """The network refused the call. Do not retry."""


def to_cents(value: object) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, int | float):
        return round(float(value) * 100)
    if isinstance(value, str):
        try:
            return round(float(value) * 100)
        except ValueError:
            return 0
    return 0


def redact_secrets(text: str) -> str:
    for secret in NETWORK_SECRETS:
        text = text.replace(secret, "***")
    return text[:200]


def make_client(
    transport: httpx.BaseTransport | None, timeout: float = 20
) -> httpx.Client:
    return httpx.Client(timeout=timeout, transport=transport)


def require(value: str, name: str) -> str:
    if not value:
        raise PermanentNetworkError(f"{name} is not configured")
    return value

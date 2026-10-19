from dataclasses import dataclass, field
from typing import Protocol

import httpx

from revenue_swarm.config import NETWORK_SECRETS
from revenue_swarm.models.affiliate_program import AffiliateProgram


@dataclass(frozen=True)
class TrackingLink:
    url: str
    network_link_id: str | None = None
    raw: dict = field(default_factory=dict)


class AffiliateNetwork(Protocol):
    name: str
    allow_redirect: bool

    def create_link(
        self, program: AffiliateProgram, destination: str, subid: str
    ) -> TrackingLink: ...


class PermanentNetworkError(Exception):
    """The network refused the call. Do not retry."""


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

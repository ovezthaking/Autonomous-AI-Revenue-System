from dataclasses import dataclass
from typing import NoReturn, Protocol

import httpx
from content_agent.tasks import redact
from revenue_swarm.models.content_item import ContentItem


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    url: str | None
    payload: dict


class TransientError(Exception):
    """Nothing eas created, safe to retry later"""


class UnknownOutcomeError(Exception):
    """The request may have been processed. Never retry automatically."""


class PermanentError(Exception):
    """The target rejected the request. Record FAILED and do not retry."""


class PublishTarget(Protocol):
    name: str

    def publish(self, item: ContentItem) -> PublishResult: ...

    def retract(self, external_id: str) -> None: ...


def raise_for_status(response: httpx.Response) -> None:
    status = response.status_code
    if status < 400:
        return
    retry_after = response.headers.get("Retry-After")
    detail = redact(response.text)
    if status == 429 or (status == 503 and retry_after):
        raise TransientError(detail)
    if 500 <= status <= 599:
        raise UnknownOutcomeError(detail)
    raise PermanentError(detail)


def raise_for_transport(exc: httpx.HTTPError) -> NoReturn:
    detail = redact(str(exc))
    if isinstance(exc, httpx.ConnectError):
        raise TransientError(detail) from exc
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout)):
        raise UnknownOutcomeError(detail) from exc
    raise UnknownOutcomeError(detail) from exc

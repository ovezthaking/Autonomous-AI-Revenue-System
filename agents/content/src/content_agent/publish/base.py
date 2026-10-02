from dataclasses import dataclass
from typing import Protocol

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

import httpx
from content_agent.publish.base import (
    PublishResult,
    raise_for_status,
    raise_for_transport,
)
from content_agent.publish.html import ensure_social_disclosure
from content_agent.settings import X_BEARER_TOKEN
from revenue_swarm.enums import PublishTargetName
from revenue_swarm.models.content_item import ContentItem


class XTarget:
    name = PublishTargetName.X.value
    limit = 280

    def publish(self, item: ContentItem) -> PublishResult:
        text = ensure_social_disclosure(item.body, self.limit)
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            try:
                response = client.post(
                    "https://api.x.com/2/tweets", json={"text": text}
                )
            except httpx.HTTPError as exc:
                raise_for_transport(exc)
        raise_for_status(response)
        data = response.json()["data"]
        external_id = str(data["id"])
        return PublishResult(
            external_id=external_id,
            url=f"https://x.com/i/web/status/{external_id}",
            payload={"text": text},
        )

    def retract(self, external_id: str) -> None:
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            try:
                response = client.post(
                    f"https://api.x.com/2/tweets/{external_id}"
                )
            except httpx.HTTPError as exc:
                raise_for_transport(exc)
        raise_for_status(response)

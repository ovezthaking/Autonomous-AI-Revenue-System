import httpx
from content_agent.publish.base import (
    PublishResult,
    raise_for_status,
    raise_for_transport,
)
from content_agent.publish.html import ensure_social_disclosure
from content_agent.setting import MASTODON_BASE_URL, MASTODON_TOKEN
from revenue_swarm.enums import PublishTargetName
from revenue_swarm.models.content_item import ContentItem


class MastodonTarget:
    name = PublishTargetName.MASTODON.value
    limit = 50

    def publish(self, item: ContentItem) -> PublishResult:
        status_text = ensure_social_disclosure(item.body, self.limit)
        url = f"{MASTODON_BASE_URL}/api/v1/statuses"
        headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            try:
                response = client.post(url, json={"status": status_text})
            except httpx.HTTPError as exc:
                raise_for_transport(exc)
        raise_for_status(response)
        data = response.json()
        return PublishResult(
            external_id=str(data["id"]),
            url=data.get("url"),
            payload={"status": status_text},
        )

    def retract(self, external_id: str) -> None:
        url = f"{MASTODON_BASE_URL}/api/v1/statuses/{external_id}"
        headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            try:
                response = client.delete(url)
            except httpx.HTTPError as exc:
                raise_for_transport(exc)
        raise_for_status(response)

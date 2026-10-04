import httpx
from content_agent.publish.base import (
    PublishResult,
    raise_for_status,
    raise_for_transport,
)
from content_agent.setting import WORDPRESS_BASE_URL
from revenue_swarm.enums import PublishTargetName


class WordPressTarget:
    name = PublishTargetName.WORDPRESS.value

    def _find_by_slug(
        self, client: httpx.Client, slug: str
    ) -> PublishResult | None:
        try:
            response = client.get(
                f"{WORDPRESS_BASE_URL}/wp-json/wp/v2/posts",
                params={"slug": slug, "status": "any"},
            )
        except httpx.HTTPError as exc:
            raise_for_transport(exc)
        raise_for_status(response)
        rows = response.json()
        if not rows:
            return None
        post = rows[0]
        return PublishResult(
            external_id=str(post["id"]),
            url=post.get("link"),
            payload={"slug": slug, "reconciled": True},
        )

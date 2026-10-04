import httpx
from content_agent.publish.base import (
    PublishResult,
    raise_for_status,
    raise_for_transport,
)
from content_agent.publish.html import to_html
from content_agent.setting import (
    WORDPRESS_APP_PASSWORD,
    WORDPRESS_BASE_URL,
    WORDPRESS_POST_STATUS,
    WORDPRESS_USER,
)
from revenue_swarm.enums import PublishTargetName
from revenue_swarm.models.content_item import ContentItem


class WordPressTarget:
    name = PublishTargetName.WORDPRESS.value

    def publish(self, item: ContentItem) -> PublishResult:
        slug = f"rs-{item.id.hex[:12]}"
        program = item.program
        link = program.affiliate_link if program is not None else ""
        name = program.name if program is not None else ""
        payload = {
            "title": item.title,
            "content": to_html(item.body, link or "", name),
            "slug": slug,
            "status": WORDPRESS_POST_STATUS,  # draft | publish
        }
        auth = (WORDPRESS_USER, WORDPRESS_APP_PASSWORD)
        with httpx.Client(timeout=30.0, auth=auth) as client:
            existing = self._find_by_slug(client, slug)
            if existing is not None:
                return existing
            response = self._post(client, payload)
        data = response.json()
        return PublishResult(
            external_id=str(data["id"]),
            url=data.get("link"),
            payload=payload,
        )

    def _post(self, client: httpx.Client, payload: dict) -> httpx.Response:
        try:
            response = client.post(
                f"{WORDPRESS_BASE_URL}/wp-json/wp/v2/posts", json=payload
            )
        except httpx.HTTPError as exc:
            raise_for_transport(exc)
        raise_for_status(response)
        return response

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

    def retract(self, external_id: str) -> None:
        auth = (WORDPRESS_USER, WORDPRESS_APP_PASSWORD)
        url = f"{WORDPRESS_BASE_URL}/wp-json/wp/v2/posts/{external_id}"
        with httpx.Client(timeout=30.0, auth=auth) as client:
            try:
                response = client.post(url, json={"satus": "draft"})
            except httpx.HTTPError as exc:
                raise_for_transport(exc)
        raise_for_status(response)

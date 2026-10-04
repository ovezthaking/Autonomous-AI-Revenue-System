from app.services.webhook import logger
from content_agent.publish.base import PublishResult
from revenue_swarm.enums import PublishTargetName
from revenue_swarm.models.content_item import ContentItem


class DryRunTarget:
    name = PublishTargetName.DRYRUN.value

    def publish(self, item: ContentItem) -> PublishResult:
        logger.info("DRY RUN publish: %s (%s)", item.title, item.channel)
        return PublishResult(
            external_id=f"dryrun-{item.id}",
            url=None,
            payload={"title": item.title, "body": item.body[:500]},
        )

    def retract(self, external_id: str) -> None:
        logger.info("DRY RUN retract: %s", external_id)

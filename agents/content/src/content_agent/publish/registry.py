from content_agent.publish.base import PublishTarget
from content_agent.publish.dryrun import DryRunTarget
from content_agent.publish.mastodon import MastodonTarget
from content_agent.publish.wordpress import WordPressTarget
from content_agent.publish.x import XTarget
from content_agent.settings import PUBLISH_TARGET_BLOG, PUBLISH_TARGET_SOCIAL
from revenue_swarm.enums import ContentChannel, PublishTargetName

TARGETS: dict[str, type[PublishTarget]] = {
    PublishTargetName.DRYRUN.value: DryRunTarget,
    PublishTargetName.WORDPRESS.value: WordPressTarget,
    PublishTargetName.MASTODON.value: MastodonTarget,
    PublishTargetName.X.value: XTarget,
}


def target_for(channel: str) -> PublishTarget:
    name = (
        PUBLISH_TARGET_BLOG
        if channel == ContentChannel.BLOG.value
        else PUBLISH_TARGET_SOCIAL
    )
    return TARGETS[name]()

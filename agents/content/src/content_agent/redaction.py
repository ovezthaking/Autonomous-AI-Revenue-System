from content_agent.settings import (
    MASTODON_TOKEN,
    WORDPRESS_APP_PASSWORD,
    X_BEARER_TOKEN,
)

SECRETS = tuple(
    s for s in (WORDPRESS_APP_PASSWORD, X_BEARER_TOKEN, MASTODON_TOKEN) if s
)


def redact(text: str) -> str:
    for secret in SECRETS:
        text = text.replace(secret, "***")
    return text[:200]

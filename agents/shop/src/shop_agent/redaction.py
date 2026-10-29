"""Error classification and secret redaction for shop-agent."""

from revenue_swarm import config


class TransientError(RuntimeError):
    """Retryable error (rate limit, temporary 5xx)."""


class PermanentError(RuntimeError):
    """Non-retryable error (validation, userErrors, auth failure)."""


class UnknownOutcomeError(RuntimeError):
    """Timeout after sending a mutation; outcome on remote is unknown."""


def _secrets() -> tuple[str, ...]:
    values = (
        config.SHOPIFY_CLIENT_SECRET,
        *config.NETWORK_SECRETS,
    )
    return tuple(dict.fromkeys(v for v in values if v))


def redact(text: str) -> str:
    for secret in _secrets():
        text = text.replace(secret, "***")
    return text[:200]

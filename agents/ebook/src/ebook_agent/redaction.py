from revenue_swarm.config import ANTHROPIC_API_KEY, STORAGE_SECRET_KEY

SECRETS = tuple(s for s in (ANTHROPIC_API_KEY, STORAGE_SECRET_KEY) if s)


def redact(text: str) -> str:
    for secret in SECRETS:
        text = text.replace(secret, "***")
    return text[:200]

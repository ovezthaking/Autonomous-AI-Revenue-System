"""Shopify Dev Dashboard client_credentials token exchange with Redis cache."""

import httpx
import redis as redis_lib
from revenue_swarm import config

TOKEN_KEY = "shopify:access_token"

redis_client = redis_lib.from_url(config.REDIS_URL)


def _decode(val: bytes | str | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return str(val)


def access_token() -> str:
    cached = _decode(redis_client.get(TOKEN_KEY))
    if cached:
        return cached
    with redis_client.lock(f"{TOKEN_KEY}:lock", timeout=30):
        cached = _decode(redis_client.get(TOKEN_KEY))
        if cached:
            return cached
        response = httpx.post(
            f"https://{config.SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.SHOPIFY_CLIENT_ID,
                "client_secret": config.SHOPIFY_CLIENT_SECRET,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        ttl = max(int(data.get("expires_in", 86400)) - 600, 60)
        token = str(data["access_token"])
        redis_client.setex(TOKEN_KEY, ttl, token)
        return token


def invalidate_token() -> None:
    redis_client.delete(TOKEN_KEY)

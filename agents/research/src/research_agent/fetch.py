import hashlib
import urllib.robotparser as robotparser
from urllib.parse import urlparse

import httpx
import redis
from revenue_swarm.config import REDIS_URL
from selectolax.parser import HTMLParser

from research_agent.settings import (
    FETCH_CACHE_TTL,
    FETCH_TIMEOUT,
    FETCH_USER_AGENT,
    RESPECT_ROBOTS,
)

MAX_BYTES = 2_000_000
_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _cache_key(url: str) -> str:
    return f"research:page:{hashlib.sha256(url.encode()).hexdigest()}"


def allowed_by_robots(url: str) -> bool:
    if not RESPECT_ROBOTS:
        return True
    parsed = urlparse(url)
    parser = robotparser.RobotFileParser()
    parser.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        parser.read()
    except Exception:
        return True
    return parser.can_fetch(FETCH_USER_AGENT, url)


def fetch_text(url: str) -> str | None:
    cached = _redis.get(_cache_key(url))
    if isinstance(cached, str):
        return cached
    if not allowed_by_robots(url):
        return None
    headers = {"User-Agent": FETCH_USER_AGENT}
    with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            return None
        html = response.text[:MAX_BYTES]
    body = HTMLParser(html).body
    if body is None:
        return None
    text = body.text(separator=" ", strip=True)
    _redis.setex(_cache_key(url), FETCH_CACHE_TTL, text)
    return text

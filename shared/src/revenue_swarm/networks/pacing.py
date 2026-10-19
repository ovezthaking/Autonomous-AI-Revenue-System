import threading
import time
from typing import cast

import redis as redis_lib

from revenue_swarm import config

_lock = threading.Lock()
_local: dict[str, tuple[float, int]] = {}
_client: redis_lib.Redis | None = None


def _redis() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.from_url(
            config.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        )
    return _client


def _count_local(key: str) -> int:
    now = time.monotonic()
    with _lock:
        started, count = _local.get(key, (now, 0))
        if now - started >= 60:
            started, count = now, 0
        count += 1
        _local[key] = (started, count)
        return count


def _count(key: str) -> int:
    try:
        client = _redis()
        count = cast(int, client.incr(key))
        if count == 1:
            client.expire(key, 60)
        return count
    except Exception:
        return _count_local(key)


def pace(name: str) -> None:
    """Slows down once a network exceeds NETWORK_RATE_LIMIT calls/min."""
    if _count(f"affiliate:pace:{name}") > config.NETWORK_RATE_LIMIT:
        time.sleep(1)

import time
from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

REQUEST_GAP_SECONDS = 1.0
_last_by_host: dict[str, float] = {}


def send(url: str, perform: Callable[[], httpx.Response]) -> httpx.Response:
    for attempt in Retrying(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    ):
        with attempt:
            pace(url)
            response = perform()
            if _is_retryable_status(response.status_code):
                response.raise_for_status()
            return response
    msg = "request retries ended without a response"
    raise RuntimeError(msg)


def pace(url: str) -> None:
    host = urlparse(url).netloc.lower()
    if not host:
        return
    now = time.monotonic()
    previous = _last_by_host.get(host)
    if previous is not None:
        delay = REQUEST_GAP_SECONDS - (now - previous)
        if delay > 0:
            time.sleep(delay)
            now = time.monotonic()
    _last_by_host[host] = now


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return _is_retryable_status(exc.response.status_code)
    return False


def _is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status <= 599

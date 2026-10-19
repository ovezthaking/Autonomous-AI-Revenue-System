"""Dead-link detection for tracked affiliate links."""

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from research_agent.settings import FETCH_USER_AGENT

PROBE_TIMEOUT = 15.0
PROBE_ATTEMPTS = 5
_HEAD_UNSUPPORTED = (405, 501)
_last_host: dict[str, float] = {}


@dataclass(frozen=True)
class ProbeVerdict:
    is_broken: bool
    reason: str


def pace_host(host: str) -> None:
    if not host:
        return
    previous = _last_host.get(host, 0.0)
    wait = previous + 1.0 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_host[host] = time.monotonic()


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _same_site(final: str, expected: str) -> bool:
    if not final or not expected:
        return True
    return (
        final == expected
        or final.endswith(f".{expected}")
        or expected.endswith(f".{final}")
    )


def _request(client: httpx.Client, url: str) -> httpx.Response:
    headers = {"User-Agent": FETCH_USER_AGENT}
    response = client.head(url, headers=headers)
    if response.status_code in _HEAD_UNSUPPORTED:
        response = client.get(url, headers=headers)
    return response


def probe(
    url: str,
    destination_url: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> ProbeVerdict:
    """Follows a tracking link and checks whether the target is still live."""
    expected_url = destination_url or url
    host = urlparse(url).netloc.lower()
    pace_host(host)

    response: httpx.Response | None = None
    with httpx.Client(
        timeout=PROBE_TIMEOUT,
        follow_redirects=True,
        transport=transport,
    ) as client:
        for _ in range(PROBE_ATTEMPTS):
            try:
                response = _request(client, url)
                break
            except (httpx.TimeoutException, httpx.ConnectError):
                continue
    if response is None:
        return ProbeVerdict(True, "five timeouts")

    code = response.status_code
    if code in (404, 410):
        return ProbeVerdict(True, str(code))
    if code == 403:
        return ProbeVerdict(True, "403")
    if code >= 500:
        return ProbeVerdict(False, f"transient {code}")

    final = urlparse(str(response.url))
    expected = urlparse(expected_url)
    if not _same_site(_host(str(response.url)), _host(expected_url)):
        return ProbeVerdict(True, "left advertiser host")
    if final.path in ("", "/") and expected.path not in ("", "/"):
        return ProbeVerdict(True, "redirected home")
    return ProbeVerdict(False, "ok")

import time

import httpx
import pytest
import research_agent.fetch as fetch_module
import research_agent.polite as polite
import research_agent.search as search_module

_ORIGINAL_SEND = httpx.Client.send
_ORIGINAL_CLIENT = httpx.Client


def _client(handler) -> type[httpx.Client]:
    transport = httpx.MockTransport(handler)

    class _Client(_ORIGINAL_CLIENT):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return _Client


def test_fetch_waits_one_second_only_for_the_same_host(monkeypatch):
    polite._last_by_host.clear()
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(fetch_module, "allowed_by_robots", lambda _url: True)
    monkeypatch.setattr(fetch_module._redis, "get", lambda _key: None)
    monkeypatch.setattr(
        fetch_module._redis, "setex", lambda *_args, **_kwargs: True
    )
    page = httpx.Response(200, text="<html><body>hello</body></html>")
    monkeypatch.setattr(
        fetch_module.httpx,
        "Client",
        _client(lambda _request: page),
    )
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    fetch_module.fetch_text("https://vendor.test/a")
    fetch_module.fetch_text("https://other.test/a")
    fetch_module.fetch_text("https://vendor.test/b")

    assert len(slept) == 1
    assert slept[0] == pytest.approx(1, abs=0.05)


def test_robots_and_page_on_the_same_host_are_one_second_apart(monkeypatch):
    import research_agent.polite as polite

    polite._last_by_host.clear()
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(fetch_module._redis, "get", lambda _key: None)
    monkeypatch.setattr(
        fetch_module._redis, "setex", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        fetch_module.robotparser.RobotFileParser, "read", lambda _self: None
    )
    monkeypatch.setattr(
        fetch_module.robotparser.RobotFileParser,
        "can_fetch",
        lambda _self, _agent, _url: True,
    )
    monkeypatch.setattr(
        fetch_module.httpx,
        "Client",
        _client(
            lambda _request: httpx.Response(
                200, text="<html><body>hello</body></html>"
            )
        ),
    )
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    fetch_module.fetch_text("https://vendor.test/program")

    assert len(slept) == 1
    assert slept[0] == pytest.approx(1, abs=0.05)


def test_search_waits_one_second_between_queries_to_the_same_api(monkeypatch):
    polite._last_by_host.clear()
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(
        search_module.httpx,
        "Client",
        _client(lambda _request: httpx.Response(200, json={"results": []})),
    )
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(seconds))

    search_module._tavily(["first query", "second query"])

    assert len(slept) == 1
    assert slept[0] == pytest.approx(1, abs=0.05)


def test_search_retries_a_transient_status_up_to_three_times(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr("research_agent.polite.REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://vendor.test/a",
                        "title": "Vendor",
                        "content": "snippet",
                        "raw_content": "raw",
                    }
                ]
            },
            request=request,
        )

    monkeypatch.setattr(search_module.httpx, "Client", _client(handler))
    hits = search_module._tavily(["query"])

    assert attempts["n"] == 3
    assert [hit.url for hit in hits] == ["https://vendor.test/a"]


def test_fetch_retries_a_server_error_then_reads_the_page(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr("research_agent.polite.REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(fetch_module, "allowed_by_robots", lambda _url: True)
    monkeypatch.setattr(fetch_module._redis, "get", lambda _key: None)
    monkeypatch.setattr(
        fetch_module._redis, "setex", lambda *_args, **_kwargs: True
    )
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, text="<html><body>Terms</body></html>")

    monkeypatch.setattr(fetch_module.httpx, "Client", _client(handler))
    text = fetch_module.fetch_text("https://vendor.test/program")

    assert attempts["n"] == 3
    assert text is not None
    assert "Terms" in text


def test_brave_retries_rate_limit_then_returns_the_hit(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr("research_agent.polite.REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(429, request=request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://vendor.test/a",
                            "title": "Vendor",
                            "description": "snippet",
                        }
                    ]
                }
            },
            request=request,
        )

    monkeypatch.setattr(search_module.httpx, "Client", _client(handler))
    hits = search_module._brave(["query"])

    assert attempts["n"] == 3
    assert [hit.url for hit in hits] == ["https://vendor.test/a"]


def test_search_does_not_retry_forbidden(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(polite, "REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(403, request=request)

    monkeypatch.setattr(search_module.httpx, "Client", _client(handler))
    with pytest.raises(httpx.HTTPStatusError) as forbidden:
        search_module._tavily(["query"])

    assert forbidden.value.response.status_code == 403
    assert attempts["n"] == 1


def test_search_does_not_retry_a_connection_error(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(polite, "REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(search_module.httpx, "Client", _client(handler))
    with pytest.raises(httpx.ConnectError):
        search_module._tavily(["query"])

    assert attempts["n"] == 1


def test_search_retries_timeouts(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(polite, "REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"results": []}, request=request)

    monkeypatch.setattr(search_module.httpx, "Client", _client(handler))
    assert search_module._tavily(["query"]) == []
    assert attempts["n"] == 3


def test_fetch_does_not_retry_not_found(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(polite, "REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(fetch_module, "allowed_by_robots", lambda _url: True)
    monkeypatch.setattr(fetch_module._redis, "get", lambda _key: None)
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(404)

    monkeypatch.setattr(fetch_module.httpx, "Client", _client(handler))
    assert fetch_module.fetch_text("https://vendor.test/missing") is None
    assert attempts["n"] == 1

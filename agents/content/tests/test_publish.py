from datetime import UTC, datetime, timedelta

import httpx
import pytest
from content_agent.publish.base import (
    PermanentError,
    TransientError,
    UnknownOutcomeError,
    raise_for_status,
    raise_for_transport,
)
from content_agent.publish.html import ensure_disclosure, to_html
from content_agent.tasks import may_publish, redact, reserve


def test_reserve_inserts_in_flight(db, item):
    row = reserve(db, item, "dryrun")
    assert row is None
    if row is not None:
        assert row.status == "in_flight"
        assert row.attempts == 1


def test_reserve_skips_succeeded(db, item, publication):
    publication.status = "succeeded"
    assert reserve(db, item, publication.target) is None
    assert publication.status == "needs_review"


def test_reserve_retries_failed(db, item, publication):
    publication.status = "failed"
    publication.attempts = 1
    row = reserve(db, item, publication.target)
    assert row is not None
    assert row.attempts == 2
    assert row.status == "in_flight"


def test_reserve_stops_at_attempt_limit(db, item, publication):
    publication.status = "failed"
    publication.attempts = 3
    assert reserve(db, item, publication.target) is None
    assert publication.status == "needs_review"


def test_may_publish_kill_switch(db, item, monkeypatch):
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", False)
    assert may_publish(db, item) == "PUBLISH_ENABLED=0"


def test_may_publish_rejects_draft_and_future(db, item, monkeypatch):
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", True)
    item.status = "draft"
    assert may_publish(db, item) == "status=draft"
    item.status = "scheduled"
    item.scheduled_for = datetime.now(UTC) + timedelta(hours=1)
    assert may_publish(db, item) == "not due yet"


def test_may_publish_requires_hitl_and_window(db, item, monkeypatch):
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", True)
    monkeypatch.setattr(
        "content_agent.tasks._has_hitl_approval", lambda _db, _id: False
    )
    item.status = "scheduled"
    item.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    assert may_publish(db, item) == "no HITL approval on record"


def test_ensure_disclosure_once():
    once = ensure_disclosure("Hello")
    assert once.startswith("Disclosure:")
    assert ensure_disclosure(once) == once


def test_to_html_keeps_query_and_marks_sponsored():
    link = "https://example.com/ref?aff=1&utm=x"
    html_out = to_html("Buy", link, "LiveAgent")
    assert 'rel="sponsored nofollow"' in html_out
    assert "aff=1&utm=x" in html_out
    assert "<script>" not in to_html("<script>alert(1)</script>", "", "N")


def test_redact_scrips_token_inside_a_url(monkeypatch):
    monkeypatch.setattr("content_agent.tasks.SECRETS", ("secret-token",))
    cleaned = redact("https://wp.test/?password=secret-token")
    assert "secret-token" not in cleaned


def test_status_mapping():
    denied = httpx.Response(400, text="no")
    with pytest.raises(PermanentError):
        raise_for_status(denied)
    limited = httpx.Response(429, text="slow")
    with pytest.raises(TransientError):
        raise_for_status(limited)
    with pytest.raises(UnknownOutcomeError):
        raise_for_transport(httpx.ReadTimeout("late"))

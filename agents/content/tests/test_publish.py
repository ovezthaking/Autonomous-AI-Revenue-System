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
from content_agent.publish.html import (
    ensure_disclosure,
    ensure_social_disclosure,
    to_html,
)
from content_agent.redaction import redact
from content_agent.tasks import may_publish, reserve

LINK = "https://twoj-link.example/ref?id=123"


def test_social_disclosure_never_truncates_the_link():
    body = "x" * 240 + "\n\n" + LINK
    out = ensure_social_disclosure(body, 280)
    assert len(out) <= 280
    assert out.count(LINK) == 1
    assert "#ad" in out.lower()


def test_social_disclosure_rejects_when_link_cannot_fit():
    with pytest.raises(ValueError):
        ensure_social_disclosure("text\n\n" + LINK, 20)


def test_reserve_inserts_in_flight(db, item):
    row = reserve(db, item, "dryrun")
    assert row is not None
    assert row.status == "in_flight"
    assert row.attempts == 1


def test_reserve_skips_succeeded(db, item, publication):
    publication.status = "succeeded"
    assert reserve(db, item, publication.target) is None
    assert publication.status == "succeeded"


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
    html_out = to_html(f"Buy {link}", link, "LiveAgent")
    assert 'rel="sponsored nofollow"' in html_out
    assert "aff=1&amp;utm=x" in html_out


def test_redact_scrips_token_inside_a_url(monkeypatch):
    monkeypatch.setattr("content_agent.redaction.SECRETS", ("secret-token",))
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
    raise_for_status(httpx.Response(200, text="ok"))
    with pytest.raises(UnknownOutcomeError):
        raise_for_status(httpx.Response(500, text="err"))
    with pytest.raises(TransientError):
        raise_for_transport(httpx.ConnectError("conn"))
    with pytest.raises(UnknownOutcomeError):
        raise_for_transport(httpx.HTTPError("other"))


def test_adapters_and_additional_branches(db, item, publication, monkeypatch):
    from unittest.mock import MagicMock

    import content_agent.worker as worker_mod
    from content_agent.publish.dryrun import DryRunTarget
    from content_agent.publish.mastodon import MastodonTarget
    from content_agent.publish.wordpress import WordPressTarget
    from content_agent.publish.x import XTarget
    from content_agent.tasks import _deliver
    from content_agent.templates import AMAZON_DISCLOSURE, render_blog

    assert worker_mod.celery_app is not None
    assert AMAZON_DISCLOSURE in render_blog(
        "Body", "Book", "https://a.co", network="amazon"
    )
    assert "#ad" in ensure_social_disclosure("no link body", 280)
    DryRunTarget().retract("dryrun-1")

    # reserve additional branches: in_flight, needs_review, retryable=False
    publication.status = "in_flight"
    assert reserve(db, item, publication.target) is None
    assert publication.status == "needs_review"

    assert reserve(db, item, publication.target) is None

    publication.status = "failed"
    publication.payload = {"retryable": False}
    assert reserve(db, item, publication.target) is None

    # may_publish outside window
    monkeypatch.setattr("content_agent.tasks.PUBLISH_ENABLED", True)
    monkeypatch.setattr(
        "content_agent.tasks._has_hitl_approval", lambda _d, _i: True
    )
    monkeypatch.setattr("content_agent.tasks._within_window", lambda _n: False)
    item.status = "scheduled"
    item.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    assert may_publish(db, item) == "outside publishing window"

    # _deliver error branches
    class _ErrTarget:
        name = "dryrun"

        def __init__(self, exc):
            self.exc = exc

        def publish(self, _item):
            raise self.exc

        def retract(self, _ext):
            return None

    assert (
        _deliver(db, item, publication, _ErrTarget(TransientError("t")))
        == "failed"
    )
    assert publication.payload["retryable"] is True
    assert (
        _deliver(db, item, publication, _ErrTarget(UnknownOutcomeError("u")))
        == "needs_review"
    )
    assert publication.status == "needs_review"
    assert (
        _deliver(db, item, publication, _ErrTarget(PermanentError("p")))
        == "failed"
    )
    assert publication.payload["retryable"] is False

    # MastodonTarget, XTarget, WordPressTarget success + HTTPError branches
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False

    # Mastodon
    fake_client.post.return_value = httpx.Response(
        200, json={"id": "m1", "url": "https://m.to/1"}
    )
    fake_client.delete.return_value = httpx.Response(200, json={})
    monkeypatch.setattr(
        "content_agent.publish.mastodon.httpx.Client",
        lambda **_kw: fake_client,
    )
    m_res = MastodonTarget().publish(item)
    assert m_res.external_id == "m1"
    MastodonTarget().retract("m1")

    fake_client.post.side_effect = httpx.ConnectError("m_conn")
    fake_client.delete.side_effect = httpx.ConnectError("m_del")
    with pytest.raises(TransientError):
        MastodonTarget().publish(item)
    with pytest.raises(TransientError):
        MastodonTarget().retract("m1")
    fake_client.post.side_effect = None
    fake_client.delete.side_effect = None

    # XTarget
    fake_client.post.return_value = httpx.Response(
        200, json={"data": {"id": "x1"}}
    )
    monkeypatch.setattr(
        "content_agent.publish.x.httpx.Client", lambda **_kw: fake_client
    )
    x_res = XTarget().publish(item)
    assert x_res.external_id == "x1"
    XTarget().retract("x1")

    fake_client.post.side_effect = httpx.ConnectError("x_conn")
    with pytest.raises(TransientError):
        XTarget().publish(item)
    with pytest.raises(TransientError):
        XTarget().retract("x1")
    fake_client.post.side_effect = None

    # WordPressTarget
    monkeypatch.setattr(
        "content_agent.publish.wordpress.httpx.Client",
        lambda **_kw: fake_client,
    )
    # 1) Reconciled existing slug
    fake_client.get.return_value = httpx.Response(
        200, json=[{"id": 77, "link": "https://wp.test/p/77"}]
    )
    wp_reconciled = WordPressTarget().publish(item)
    assert wp_reconciled.external_id == "77"

    # 2) Not found by slug -> creates new post
    fake_client.get.return_value = httpx.Response(200, json=[])
    fake_client.post.return_value = httpx.Response(
        201, json={"id": 88, "link": "https://wp.test/p/88"}
    )
    wp_created = WordPressTarget().publish(item)
    assert wp_created.external_id == "88"
    WordPressTarget().retract("88")

    # 3) Transport errors in _find_by_slug, _post, retract
    fake_client.get.side_effect = httpx.ConnectError("wp_get")
    with pytest.raises(TransientError):
        WordPressTarget().publish(item)
    fake_client.get.side_effect = None
    fake_client.get.return_value = httpx.Response(200, json=[])
    fake_client.post.side_effect = httpx.ConnectError("wp_post")
    with pytest.raises(TransientError):
        WordPressTarget().publish(item)
    with pytest.raises(TransientError):
        WordPressTarget().retract("88")

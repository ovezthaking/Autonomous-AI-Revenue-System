import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from research_agent.agent import _drop_known, _still_blocked
from research_agent.models import Candidate as WebCandidate, ProgramFacts
from research_agent.probe import probe
from research_agent.tasks import check_links, check_pending
from revenue_swarm import config
from revenue_swarm.enums import ApplicationStatus, LinkStatus, ProgramStatus
from revenue_swarm.links import ensure_link, public_url, subid_for
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.networks import (
    AmazonNetwork,
    AwinNetwork,
    CjNetwork,
    ImpactNetwork,
    ManualNetwork,
    PermanentNetworkError,
)
from sqlalchemy import func, select

_ORIGINAL_SEND = httpx.Client.send


def _program(**overrides) -> AffiliateProgram:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Acme CRM",
        "url": "https://shop.test/product/crm",
        "network": "awin",
        "network_program_id": "1234",
        "status": ProgramStatus.APPROVED.value,
        "application_status": ApplicationStatus.ACTIVE.value,
        "allow_redirect": True,
    }
    defaults.update(overrides)
    return AffiliateProgram(**defaults)


def test_subid_is_hex():
    item = ContentItem(id=uuid.uuid4(), title="t", body="b")
    subid = subid_for(item)
    assert len(subid) == 32
    assert not set("&+#'\"|") & set(subid)


def test_amazon_public_url_skips_go(monkeypatch):
    monkeypatch.setattr(config, "SITE_URL", "https://mysite.test")
    program = AffiliateProgram(network="amazon", allow_redirect=False)
    link = AffiliateLink(
        program=program,
        network="amazon",
        destination_url="https://www.amazon.com/dp/X",
        tracking_url="https://www.amazon.com/dp/X?tag=me-20&ascsubtag=abc",
        slug="abc",
        subid="abc",
    )
    assert "/go/" not in public_url(link)
    assert public_url(link) == link.tracking_url


def test_non_amazon_public_url_uses_go(monkeypatch):
    monkeypatch.setattr(config, "SITE_URL", "https://mysite.test")
    program = AffiliateProgram(network="awin", allow_redirect=True)
    link = AffiliateLink(
        program=program,
        network="awin",
        destination_url="https://shop.test/p",
        tracking_url="https://www.awin1.com/cread.php?id=1",
        slug="xyz123",
        subid="abc",
    )
    assert public_url(link) == "https://mysite.test/go/xyz123"


def test_awin_create_link_and_unknown_error(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(config, "AWIN_PUBLISHER_ID", "999")
    monkeypatch.setattr(config, "AWIN_API_TOKEN", "secret-token")

    captured: list[dict] = []

    def ok_handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            json={"url": "https://www.awin1.com/cread.php?clickref=abc123"},
        )

    net = AwinNetwork(transport=httpx.MockTransport(ok_handler))
    res = net.create_link(_program(), "https://shop.test/p", "abc123")
    assert res.url == "https://www.awin1.com/cread.php?clickref=abc123"
    assert captured[0] == {
        "advertiserId": "1234",
        "destinationUrl": "https://shop.test/p",
        "parameters": {"clickref": "abc123"},
    }

    def err_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text="Unknown error! Please try again later!"
        )

    net_err = AwinNetwork(transport=httpx.MockTransport(err_handler))
    with pytest.raises(PermanentNetworkError, match="link builder disabled"):
        net_err.create_link(_program(), "https://shop.test/p", "abc123")


def test_awin_rejects_bad_clickref_and_large_batch(monkeypatch):
    monkeypatch.setattr(config, "AWIN_PUBLISHER_ID", "999")
    monkeypatch.setattr(config, "AWIN_API_TOKEN", "secret-token")
    net = AwinNetwork()
    with pytest.raises(PermanentNetworkError, match="clickref"):
        net.create_link(_program(), "https://shop.test", "BAD#REF")

    many = [(_program(), "https://shop.test", "abc") for _ in range(101)]
    with pytest.raises(PermanentNetworkError, match="batch larger than 100"):
        net.create_links(many)


def test_impact_basic_auth_and_403(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(config, "IMPACT_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(config, "IMPACT_AUTH_TOKEN", "tok456")

    def handler_403(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization", "").startswith("Basic ")
        return httpx.Response(403, text="Vanity limit exceeded")

    net = ImpactNetwork(transport=httpx.MockTransport(handler_403))
    with pytest.raises(PermanentNetworkError, match="vanity limit"):
        net.create_link(_program(network="impact"), "https://shop.test", "s1")

    def handler_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"TrackingLink": "https://imp.i123.net/c/1", "Id": "L1"}
        )

    net_ok = ImpactNetwork(transport=httpx.MockTransport(handler_ok))
    tracked = net_ok.create_link(
        _program(network="impact"), "https://shop.test", "s1"
    )
    assert tracked.url == "https://imp.i123.net/c/1"
    assert tracked.network_link_id == "L1"


def test_cj_and_manual_and_amazon_adapters(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(config, "CJ_API_KEY", "cj-secret")
    monkeypatch.setattr(config, "AMAZON_PARTNER_TAG", "mytag-20")

    def cj_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["sid"] == "sub1"
        return httpx.Response(
            200, json={"trackingUrl": "https://www.anrdoezrs.net/links/1"}
        )

    cj = CjNetwork(transport=httpx.MockTransport(cj_handler))
    assert (
        cj.create_link(_program(network="cj"), "https://shop.test", "sub1").url
        == "https://www.anrdoezrs.net/links/1"
    )

    manual_prog = _program(
        network="manual", affiliate_link="https://partner.test/ref?id=7"
    )
    manual_link = ManualNetwork().create_link(
        manual_prog, "https://partner.test", "sub99"
    )
    assert "id=7" in manual_link.url
    assert "subid=sub99" in manual_link.url

    amz_prog = _program(network="amazon", allow_redirect=False)
    amz_link = AmazonNetwork().create_link(
        amz_prog, "https://www.amazon.com/dp/B001", "subamz"
    )
    assert "tag=mytag-20" in amz_link.url
    assert "ascsubtag=subamz" in amz_link.url


def test_probe_verdicts(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr("research_agent.probe.pace_host", lambda _h: None)

    def handler_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    v_404 = probe(
        "https://shop.test/product/1",
        transport=httpx.MockTransport(handler_404),
    )
    assert v_404.is_broken is True
    assert v_404.reason == "404"

    def handler_home(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/product/1":
            return httpx.Response(
                302,
                headers={"Location": "https://shop.test/"},
                request=request,
            )
        return httpx.Response(200, request=request)

    v_home = probe(
        "https://shop.test/product/1",
        transport=httpx.MockTransport(handler_home),
    )
    assert v_home.is_broken is True
    assert v_home.reason == "redirected home"

    def handler_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)

    v_ok = probe(
        "https://shop.test/product/1",
        transport=httpx.MockTransport(handler_ok),
    )
    assert v_ok.is_broken is False
    assert v_ok.reason == "ok"


def test_still_blocked_cooldown():
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    future = {"declined_until": "2027-01-01T00:00:00Z"}
    past = {"declined_until": "2026-01-01T00:00:00Z"}
    assert _still_blocked(future, now) is True
    assert _still_blocked(past, now) is False
    assert _still_blocked(None, now) is False


@pytest.mark.integration
def test_ensure_link_twice_is_one_row(
    db_session, make_program, make_content_item, monkeypatch
):
    monkeypatch.setattr(config, "AFFILIATE_LINKS_ENABLED", True)
    program = make_program(
        status="approved",
        application_status="active",
        network="manual",
        affiliate_link="https://shop.test/ref?p=1",
        url="https://shop.test/item",
    )
    item = make_content_item(affiliate_program_id=program.id)

    first = ensure_link(db_session, program, item)
    second = ensure_link(db_session, program, item)
    db_session.commit()

    assert first.id == second.id
    count = db_session.scalar(
        select(func.count())
        .select_from(AffiliateLink)
        .where(AffiliateLink.program_id == program.id)
    )
    assert count == 1


@pytest.mark.integration
def test_check_links_and_pending_tasks(
    db_session, make_program, make_content_item, monkeypatch
):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(config, "AFFILIATE_LINKS_ENABLED", True)
    monkeypatch.setattr(config, "LINK_CHECK_ENABLED", True)
    now = datetime.now(UTC)

    pending_prog = make_program(
        status="approved",
        application_status="pending",
        applied_at=now - timedelta(days=15),
    )
    res_pending = check_pending(db_session, now=now)
    assert res_pending["reminders"] >= 1
    db_session.refresh(pending_prog)
    assert pending_prog.extras is not None
    assert pending_prog.extras.get("needs_reminder") is True

    active_prog = make_program(
        status="approved",
        application_status="active",
        network="manual",
        affiliate_link="https://shop.test/p/dead",
        url="https://shop.test/p/dead",
    )
    item = make_content_item(affiliate_program_id=active_prog.id)
    link = ensure_link(db_session, active_prog, item)
    link.created_at = now - timedelta(days=40)
    db_session.commit()

    monkeypatch.setattr(
        "research_agent.tasks.probe",
        lambda *_a, **_kw: probe(
            "https://shop.test/p/dead",
            transport=httpx.MockTransport(
                lambda req: httpx.Response(404, request=req)
            ),
        ),
    )
    monkeypatch.setattr("research_agent.probe.pace_host", lambda _h: None)

    result = check_links(db_session, now=now)
    assert result["checked"] >= 1
    assert result["broken"] == 1
    db_session.refresh(link)
    db_session.refresh(item)
    assert link.status == LinkStatus.BROKEN.value
    assert item.extras and item.extras.get("link_review") == "404"


@pytest.mark.integration
def test_declined_program_returns_after_cooldown(db_session, make_program):
    past = (datetime.now(UTC) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    make_program(
        name="ExpiredDecline",
        url="https://expired-decline.test/aff",
        status="approved",
        application_status="declined",
        extras={"declined_until": past},
    )
    candidate = WebCandidate(
        name="ExpiredDecline",
        url="https://expired-decline.test/aff",
        evidence_url="https://expired-decline.test/aff",
        facts=ProgramFacts(
            program_name="ExpiredDecline",
            commission_type="recurring",
            commission_value=20.0,
            confidence=0.9,
        ),
        score=50.0,
        score_breakdown={},
    )
    fresh = _drop_known(db_session, [candidate])
    assert len(fresh) == 1

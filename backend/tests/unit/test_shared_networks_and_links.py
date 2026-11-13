"""Unit tests for revenue_swarm.networks and revenue_swarm.links."""

import uuid
from datetime import date
from unittest.mock import MagicMock

import httpx
import pytest
from revenue_swarm import config, links, networks
from revenue_swarm.enums import ApplicationStatus
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
    active_networks,
    base as net_base,
    network_for,
    pacing,
)


def _program(
    network: str = "awin",
    program_id: str | None = "1001",
    affiliate_link: str | None = "https://fallback.test/ref",
    status: str = ApplicationStatus.ACTIVE.value,
) -> AffiliateProgram:
    prog = AffiliateProgram(
        id=uuid.uuid4(),
        name="TestProg",
        url="https://merchant.test/product",
        network=network,
        network_program_id=program_id,
        affiliate_link=affiliate_link,
        application_status=status,
        allow_redirect=(network != "amazon"),
    )
    return prog


def test_network_registry_base_helpers_and_simple_networks(monkeypatch):
    # 1. network_for & active_networks
    assert isinstance(network_for("awin"), AwinNetwork)
    assert isinstance(network_for("impact"), ImpactNetwork)
    assert isinstance(network_for("cj"), CjNetwork)
    assert isinstance(network_for("amazon"), AmazonNetwork)
    assert isinstance(network_for("manual"), ManualNetwork)

    monkeypatch.setattr(config, "AFFILIATE_NETWORKS", "awin, cj , manual")
    active = active_networks()
    assert [n.name for n in active] == ["awin", "cj", "manual"]

    # 2. base helpers: to_cents, redact_secrets, make_client, require
    assert net_base.to_cents(None) == 0
    assert net_base.to_cents("") == 0
    assert net_base.to_cents(12.34) == 1234
    assert net_base.to_cents("12.34") == 1234
    assert net_base.to_cents("not-a-num") == 0
    assert net_base.to_cents(object()) == 0

    monkeypatch.setattr(net_base, "NETWORK_SECRETS", ("topsecret",))
    assert net_base.redact_secrets("token=topsecret!") == "token=***!"

    client = net_base.make_client(None, timeout=5)
    client.close()

    with pytest.raises(PermanentNetworkError, match="FOO is not configured"):
        net_base.require("", "FOO")

    # 3. ManualNetwork & AmazonNetwork
    today = date(2026, 10, 1)
    assert ManualNetwork().fetch_performance(today, today) == []
    assert AmazonNetwork().fetch_performance(today, today) == []

    monkeypatch.setattr(config, "AMAZON_PARTNER_TAG", "mytag-20")
    amz_link = AmazonNetwork().create_link(
        _program("amazon"), "https://amazon.com/dp/B01", "sub123"
    )
    assert "tag=mytag-20" in amz_link.url
    assert "ascsubtag=sub123" in amz_link.url


def test_pacing_redis_and_local_fallback(monkeypatch):
    fake_redis = MagicMock()
    fake_redis.incr.side_effect = [1, 100]
    monkeypatch.setattr(pacing, "_client", None)
    monkeypatch.setattr(
        pacing.redis_lib, "from_url", lambda *_a, **_kw: fake_redis
    )
    monkeypatch.setattr(config, "NETWORK_RATE_LIMIT", 50)

    slept = []
    monkeypatch.setattr(pacing.time, "sleep", lambda s: slept.append(s))

    # First call: count == 1 -> sets expire, does not sleep
    pacing.pace("awin")
    fake_redis.expire.assert_called_once()
    assert slept == []

    # Second call: count == 100 > 50 -> sleeps 1s
    pacing.pace("awin")
    assert slept == [1]

    # Redis error -> falls back to _count_local (with window reset >= 60s)
    fake_redis.incr.side_effect = RuntimeError("redis down")
    clock = [1000.0]
    monkeypatch.setattr(pacing.time, "monotonic", lambda: clock[0])
    pacing._local.clear()

    assert pacing._count("k_local") == 1
    assert pacing._count("k_local") == 2
    clock[0] = 1061.0
    assert pacing._count("k_local") == 1


def test_awin_network_links_and_performance(monkeypatch):
    monkeypatch.setattr(config, "AWIN_PUBLISHER_ID", "pub1")
    monkeypatch.setattr(config, "AWIN_API_TOKEN", "tok1")
    monkeypatch.setattr("revenue_swarm.networks.awin.pace", lambda _n: None)

    prog = _program("awin", program_id="100")

    # Validation errors in _item and batch size
    with pytest.raises(PermanentNetworkError, match="clickref rejected"):
        AwinNetwork().create_link(prog, "https://m.test", "BAD_UPPER")

    prog_no_id = _program("awin", program_id=None)
    with pytest.raises(
        PermanentNetworkError, match="network_program_id missing"
    ):
        AwinNetwork().create_link(prog_no_id, "https://m.test", "valid1")

    with pytest.raises(PermanentNetworkError, match="batch larger than 100"):
        AwinNetwork().create_links([(prog, "https://m.test", "valid1")] * 101)

    # HTTP responses via MockTransport
    responses = [
        httpx.Response(200, text="Unknown error"),
        httpx.Response(401, text="Unauthorized"),
        httpx.Response(
            200, json=[{"url": "https://awin1.com/1", "id": "id1"}]
        ),
        httpx.Response(200, json=[{"url": "https://awin1.com/2"}]),
        httpx.Response(403, text="Forbidden"),
        httpx.Response(
            200,
            json=[
                {
                    "date": "2026-10-15",
                    "advertiserId": 100,
                    "clickRef": "sub1",
                    "clicks": 10,
                    "pendingNo": 1,
                    "approvedNo": 2,
                    "declinedNo": 0,
                    "pendingValue": 5.5,
                    "approvedValue": "12.00",
                    "currency": "EUR",
                }
            ],
        ),
    ]
    transport = httpx.MockTransport(lambda _req: responses.pop(0))
    net = AwinNetwork(transport=transport)

    with pytest.raises(PermanentNetworkError, match="link builder disabled"):
        net.create_link(prog, "https://m.test", "sub1")

    with pytest.raises(PermanentNetworkError, match="awin 401"):
        net.create_link(prog, "https://m.test", "sub1")

    single = net.create_link(prog, "https://m.test", "sub1")
    assert single.url == "https://awin1.com/1"

    batch = net.create_links([(prog, "https://m.test", "sub1")])
    assert len(batch) == 1
    assert batch[0].url == "https://awin1.com/2"

    today = date(2026, 10, 15)
    with pytest.raises(PermanentNetworkError, match="awin 403"):
        net.fetch_performance(today, today)

    rows = net.fetch_performance(today, today)
    assert len(rows) == 1
    assert rows[0].revenue_approved_cents == 1200
    assert rows[0].currency == "EUR"


def test_cj_and_impact_networks(monkeypatch):
    monkeypatch.setattr(config, "CJ_API_KEY", "cj_key")
    monkeypatch.setattr(config, "IMPACT_ACCOUNT_SID", "imp_sid")
    monkeypatch.setattr(config, "IMPACT_AUTH_TOKEN", "imp_tok")
    monkeypatch.setattr("revenue_swarm.networks.cj.pace", lambda _n: None)
    monkeypatch.setattr("revenue_swarm.networks.impact.pace", lambda _n: None)

    today = date(2026, 10, 15)

    # 1. CjNetwork
    prog_no_id = _program("cj", program_id=None)
    with pytest.raises(PermanentNetworkError):
        CjNetwork().create_link(prog_no_id, "https://m.test", "s1")

    cj_responses = [
        httpx.Response(400, text="Bad"),
        httpx.Response(
            200, json={"trackingUrl": "https://cj.test/1", "linkId": "L1"}
        ),
        httpx.Response(401, text="Unauth"),
        httpx.Response(
            200,
            json={
                "records": [
                    {
                        "date": "2026-10-15",
                        "programId": "200",
                        "sid": "s1",
                        "clicks": 4,
                        "approvedValue": 9.0,
                    }
                ]
            },
        ),
    ]
    cj = CjNetwork(
        transport=httpx.MockTransport(lambda _r: cj_responses.pop(0))
    )
    prog_cj = _program("cj", program_id="200")

    with pytest.raises(PermanentNetworkError, match="cj 400"):
        cj.create_link(prog_cj, "https://m.test", "s1")

    assert cj.create_link(prog_cj, "https://m.test", "s1").url == (
        "https://cj.test/1"
    )

    with pytest.raises(PermanentNetworkError, match="cj 401"):
        cj.fetch_performance(today, today)

    cj_rows = cj.fetch_performance(today, today)
    assert len(cj_rows) == 1
    assert cj_rows[0].revenue_approved_cents == 900

    # 2. ImpactNetwork
    with pytest.raises(PermanentNetworkError):
        ImpactNetwork().create_link(prog_no_id, "https://m.test", "s1")

    imp_responses = [
        httpx.Response(403, text="Vanity cap"),
        httpx.Response(400, text="Bad"),
        httpx.Response(
            200, json={"TrackingLink": "https://imp.test/1", "Id": "I1"}
        ),
        httpx.Response(404, text="Missing"),
        httpx.Response(
            200,
            json={
                "Records": [
                    {
                        "Date": "2026-10-15",
                        "CampaignId": "300",
                        "subId1": "s1",
                        "Clicks": 7,
                        "Payout": "15.00",
                    }
                ]
            },
        ),
    ]
    imp = ImpactNetwork(
        transport=httpx.MockTransport(lambda _r: imp_responses.pop(0))
    )
    prog_imp = _program("impact", program_id="300")

    with pytest.raises(PermanentNetworkError, match="vanity limit"):
        imp.create_link(prog_imp, "https://m.test", "s1")

    with pytest.raises(PermanentNetworkError, match="impact 400"):
        imp.create_link(prog_imp, "https://m.test", "s1")

    assert imp.create_link(prog_imp, "https://m.test", "s1").url == (
        "https://imp.test/1"
    )

    with pytest.raises(PermanentNetworkError, match="impact 404"):
        imp.fetch_performance(today, today)

    imp_rows = imp.fetch_performance(today, today)
    assert len(imp_rows) == 1
    assert imp_rows[0].revenue_approved_cents == 1500


def test_links_ensure_public_url_and_link_for_content(monkeypatch):
    db = MagicMock()
    item = ContentItem(
        id=uuid.uuid4(), title="Post", body="Body", channel="blog"
    )
    prog = _program("manual", affiliate_link="https://m.test/ref")

    # 1. Disabled affiliate links or inactive program -> RuntimeError
    monkeypatch.setattr(config, "AFFILIATE_LINKS_ENABLED", False)
    with pytest.raises(RuntimeError, match="affiliate links disabled"):
        links.ensure_link(db, prog, item)

    monkeypatch.setattr(config, "AFFILIATE_LINKS_ENABLED", True)
    prog_inactive = _program("manual", status=ApplicationStatus.PENDING.value)
    with pytest.raises(RuntimeError, match="program is not active"):
        links.ensure_link(db, prog_inactive, item)

    # 2. Existing link returned directly
    existing_link = AffiliateLink(
        program_id=prog.id,
        content_item_id=item.id,
        destination_url=prog.url or "",
        tracking_url="https://m.test/ref?subid=1",
        slug="slug1",
        subid=item.id.hex,
        network="manual",
    )
    existing_link.program = prog
    db.scalar.return_value = existing_link
    assert links.ensure_link(db, prog, item) is existing_link

    # 3. Creating new link with SITE_URL UTM tagging
    db.scalar.return_value = None
    monkeypatch.setattr(config, "SITE_URL", "https://merchant.test")
    created = links.ensure_link(db, prog, item)
    assert created.subid == item.id.hex
    assert (
        links.public_url(created) == f"https://merchant.test/go/{created.slug}"
    )

    # Direct URL for amazon
    amz_prog = _program("amazon")
    created.network = "amazon"
    created.program = amz_prog
    assert links.public_url(created) == created.tracking_url

    # 4. link_for_content: success, fallback, and error when no fallback
    created.network = "manual"
    created.program = prog
    db.scalar.return_value = created
    assert links.link_for_content(db, prog, item).endswith(
        f"/go/{created.slug}"
    )

    # PermanentNetworkError falls back to affiliate_link and sets link_error
    monkeypatch.setattr(
        links,
        "ensure_link",
        MagicMock(side_effect=PermanentNetworkError("api down")),
    )
    assert links.link_for_content(db, prog, item) == "https://m.test/ref"
    assert prog.extras["link_error"] == "api down"

    # PermanentNetworkError without affiliate_link re-raises
    prog.affiliate_link = None
    with pytest.raises(PermanentNetworkError, match="api down"):
        links.link_for_content(db, prog, item)

    # Tracking disabled without affiliate_link raises PermanentNetworkError
    monkeypatch.setattr(config, "AFFILIATE_LINKS_ENABLED", False)
    with pytest.raises(
        PermanentNetworkError, match="no affiliate link available"
    ):
        links.link_for_content(db, prog, item)

    prog.affiliate_link = "https://m.test/fallback"
    assert links.link_for_content(db, prog, item) == "https://m.test/fallback"
    assert networks.KNOWN_NETWORKS is not None

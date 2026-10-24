import pytest
from revenue_swarm import config
from revenue_swarm.enums import ApplicationStatus, LinkStatus
from revenue_swarm.models.affiliate_link import AffiliateLink
from revenue_swarm.models.link_click import LinkClick
from sqlalchemy import func, select

pytestmark = pytest.mark.integration


def test_applications_lifecycle_and_amazon_constraint(client, make_program):
    prog = make_program(status="approved", url="https://amazon.com/dp/B01")

    res = client.get("/applications")
    assert res.status_code == 200
    assert any(row["id"] == str(prog.id) for row in res.json())

    applied = client.post(f"/applications/{prog.id}/applied")
    assert applied.status_code == 200
    assert (
        applied.json()["application_status"] == ApplicationStatus.PENDING.value
    )
    assert applied.json()["applied_at"] is not None

    active = client.post(
        f"/applications/{prog.id}/active",
        json={"network": "amazon", "network_program_id": "amz-1"},
    )
    assert active.status_code == 200
    assert (
        active.json()["application_status"] == ApplicationStatus.ACTIVE.value
    )
    assert active.json()["allow_redirect"] is False


def test_application_declined_sets_cooldown(client, make_program):
    prog = make_program(status="approved")
    declined = client.post(f"/applications/{prog.id}/declined")
    assert declined.status_code == 200
    data = declined.json()
    assert data["application_status"] == ApplicationStatus.DECLINED.value
    assert "declined_until" in (data["extras"] or {})


def test_go_redirect_logs_click_and_retired_falls_back(
    client, db_session, make_program, monkeypatch
):
    monkeypatch.setattr(config, "LINK_REDIRECT_ENABLED", True)
    monkeypatch.setattr(config, "LINK_FALLBACK_URL", "https://fallback.test")

    prog = make_program(
        status="approved",
        application_status="active",
        network="manual",
        affiliate_link="https://shop.test/ref?id=1",
    )
    active_link = AffiliateLink(
        program_id=prog.id,
        destination_url="https://shop.test/p",
        tracking_url="https://shop.test/ref?id=1&subid=abc",
        slug="live-slug",
        subid="abc",
        network="manual",
        status=LinkStatus.ACTIVE.value,
    )
    retired_link = AffiliateLink(
        program_id=prog.id,
        destination_url="https://shop.test/old",
        tracking_url="https://shop.test/ref?id=1&subid=old",
        slug="old-slug",
        subid="old",
        network="manual",
        status=LinkStatus.RETIRED.value,
    )
    db_session.add_all([active_link, retired_link])
    db_session.commit()

    res_ok = client.get(
        "/go/live-slug",
        headers={"user-agent": "Mozilla/5.0", "cf-ipcountry": "PL"},
        follow_redirects=False,
    )
    assert res_ok.status_code == 302
    assert res_ok.headers["location"] == "https://shop.test/ref?id=1&subid=abc"

    clicks = db_session.scalars(
        select(LinkClick).where(LinkClick.link_id == active_link.id)
    ).all()
    assert len(clicks) == 1
    assert clicks[0].country == "PL"
    assert len(clicks[0].user_agent_hash or "") == 16

    res_retired = client.get("/go/old-slug", follow_redirects=False)
    assert res_retired.status_code == 302
    assert res_retired.headers["location"] == "https://fallback.test"

    res_missing = client.get("/go/does-not-exist", follow_redirects=False)
    assert res_missing.status_code == 302
    assert res_missing.headers["location"] == "https://fallback.test"

    total_clicks = db_session.scalar(
        select(func.count()).select_from(LinkClick)
    )
    assert total_clicks == 1


def test_broken_links_list_and_repair(client, db_session, make_program):
    prog = make_program(
        status="approved",
        application_status="active",
        network="manual",
        affiliate_link="https://shop.test/ref?id=1",
    )
    broken = AffiliateLink(
        program_id=prog.id,
        destination_url="https://shop.test/dead",
        tracking_url="https://shop.test/ref?id=1&subid=s1",
        slug="broken-slug",
        subid="s1",
        network="manual",
        status=LinkStatus.BROKEN.value,
    )
    db_session.add(broken)
    db_session.commit()

    listed = client.get("/links?status=broken")
    assert listed.status_code == 200
    assert any(item["slug"] == "broken-slug" for item in listed.json())

    repaired = client.patch(
        f"/links/{broken.id}",
        json={"destination_url": "https://shop.test/alive"},
    )
    assert repaired.status_code == 200
    assert repaired.json()["status"] == LinkStatus.ACTIVE.value
    assert repaired.json()["destination_url"] == "https://shop.test/alive"
    assert "subid=s1" in repaired.json()["tracking_url"]


def test_metrics_by_content_attribution(
    client, db_session, make_program, make_content_item, monkeypatch
):
    from datetime import date

    from revenue_swarm.enums import (
        OrderStatus,
        ProductStatus,
        PublicationStatus,
    )
    from revenue_swarm.models.affiliate_metric import AffiliateMetric
    from revenue_swarm.models.order import Order
    from revenue_swarm.models.product import Product
    from revenue_swarm.models.publication import Publication

    monkeypatch.setattr(config, "TOKEN_CENTS", 2)

    prog = make_program(
        status="approved",
        application_status="active",
        network="awin",
        network_program_id="100",
    )
    item = make_content_item(
        title="Best CRM Comparison",
        extras={"tokens_used": 150},
    )
    subid = item.id.hex

    link = AffiliateLink(
        program_id=prog.id,
        content_item_id=item.id,
        destination_url="https://shop.test/crm",
        tracking_url=f"https://www.awin1.com/cread.php?clickref={subid}",
        slug="crm-slug",
        subid=subid,
        network="awin",
        status=LinkStatus.ACTIVE.value,
    )
    db_session.add(link)
    db_session.flush()

    db_session.add_all(
        [
            LinkClick(link_id=link.id, country="PL"),
            LinkClick(link_id=link.id, country="DE"),
            AffiliateMetric(
                network="awin",
                program_id=prog.id,
                subid=subid,
                day=date(2026, 10, 15),
                clicks=20,
                conversions_approved=3,
                conversions_pending=1,
                revenue_approved_cents=4500,
                revenue_pending_cents=1500,
                currency="USD",
            ),
            Publication(
                content_item_id=item.id,
                target="wordpress",
                status=PublicationStatus.SUCCEEDED.value,
                external_url="https://blog.test/best-crm-comparison",
            ),
        ]
    )

    product = Product(
        slug="crm-handbook",
        title="CRM Handbook",
        price_cents=2900,
        currency="USD",
        status=ProductStatus.LIVE.value,
    )
    db_session.add(product)
    db_session.flush()

    db_session.add_all(
        [
            Order(
                product_id=product.id,
                provider="fake",
                provider_session_id="sess-fulfilled",
                amount_cents=2900,
                currency="USD",
                status=OrderStatus.FULFILLED.value,
                source=subid,
            ),
            Order(
                product_id=product.id,
                provider="fake",
                provider_session_id="sess-pending",
                amount_cents=2900,
                currency="USD",
                status=OrderStatus.PENDING.value,
                source=subid,
            ),
        ]
    )
    db_session.commit()

    res = client.get("/metrics/by-content")
    assert res.status_code == 200
    rows = res.json()
    matched = next(r for r in rows if r["id"] == str(item.id))
    assert matched["title"] == "Best CRM Comparison"
    assert matched["publication"] == "https://blog.test/best-crm-comparison"
    assert matched["clicks"] == 2
    assert matched["conversions"] == 3
    assert matched["affiliate_cents"] == 4500
    assert matched["pending_cents"] == 1500
    assert matched["own_cents"] == 2900
    assert matched["cost_cents"] == 300

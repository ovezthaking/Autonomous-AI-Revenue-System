import uuid
from datetime import date
from decimal import Decimal

import httpx
from research_agent.epc import real_epc, smoothed_epc
from research_agent.tasks import (
    _upsert_metric,
    rescore_proposed,
    sync_performance,
)
from revenue_swarm import config
from revenue_swarm.models.affiliate_metric import AffiliateMetric
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks import (
    AmazonNetwork,
    AwinNetwork,
    CjNetwork,
    ImpactNetwork,
    ManualNetwork,
    PerformanceRow,
)
from sqlalchemy import select

_ORIGINAL_SEND = httpx.Client.send


def _performance(**overrides) -> PerformanceRow:
    defaults = {
        "day": date(2026, 10, 1),
        "program_id": "1234",
        "subid": "subid001",
        "clicks": 10,
        "conversions_pending": 0,
        "conversions_approved": 1,
        "conversions_declined": 0,
        "revenue_pending_cents": 0,
        "revenue_approved_cents": 2500,
        "currency": "USD",
    }
    defaults.update(overrides)
    return PerformanceRow(**defaults)


def _metric(
    db,
    program_id: uuid.UUID,
    *,
    day: date | None = None,
    clicks: int = 100,
    revenue_approved_cents: int = 5000,
    revenue_pending_cents: int = 0,
) -> AffiliateMetric:
    row = AffiliateMetric(
        network="awin",
        program_id=program_id,
        subid="sub1",
        day=day or date.today(),
        clicks=clicks,
        conversions_approved=1,
        revenue_approved_cents=revenue_approved_cents,
        revenue_pending_cents=revenue_pending_cents,
        currency="USD",
    )
    db.add(row)
    db.flush()
    return row


def test_upsert_same_day_keeps_one_row(db_session, make_program):
    prog = make_program(network="awin", network_program_id="1234")
    row = _performance(day=date(2026, 10, 1), conversions_pending=2)
    _upsert_metric(db_session, "awin", row)
    later = _performance(
        day=date(2026, 10, 1),
        conversions_pending=0,
        conversions_declined=2,
    )
    _upsert_metric(db_session, "awin", later)
    db_session.commit()
    stored = db_session.scalars(select(AffiliateMetric)).all()
    assert len(stored) == 1
    assert stored[0].program_id == prog.id
    assert stored[0].conversions_declined == 2
    assert stored[0].conversions_pending == 0


def test_upsert_same_day_without_program_keeps_one_row(db_session):
    row = _performance(
        day=date(2026, 10, 2),
        program_id="unmapped-adv",
        conversions_pending=3,
    )
    _upsert_metric(db_session, "awin", row)
    later = _performance(
        day=date(2026, 10, 2),
        program_id="unmapped-adv",
        conversions_pending=1,
        conversions_approved=2,
    )
    _upsert_metric(db_session, "awin", later)
    db_session.commit()
    stored = db_session.scalars(select(AffiliateMetric)).all()
    assert len(stored) == 1
    assert stored[0].program_id is None
    assert stored[0].conversions_pending == 1
    assert stored[0].conversions_approved == 2


def test_real_epc_needs_a_hundred_clicks(db_session, make_program):
    prog = make_program()
    _metric(
        db_session,
        prog.id,
        clicks=12,
        revenue_approved_cents=5000,
        revenue_pending_cents=99999,
    )
    assert real_epc(db_session, prog.id) is None

    _metric(
        db_session,
        prog.id,
        day=date.today().replace(day=max(1, date.today().day - 1)),
        clicks=88,
        revenue_approved_cents=5000,
        revenue_pending_cents=99999,
    )
    measured = real_epc(db_session, prog.id)
    assert measured == Decimal("1.00")


def test_smoothed_epc_trusts_a_large_sample():
    small = smoothed_epc(10, 10_000, category_epc=0.2)
    large = smoothed_epc(10_000, 10_000_000, category_epc=0.2)
    assert abs(small - 0.2) < abs(large - 0.2)


def _program_with_operator_epc(
    db, make_program, *, operator: float | None, clicks: int
) -> AffiliateProgram:
    facts = {
        "program_name": "Acme Helpdesk",
        "commission_type": "percent_recurring",
        "commission_value": 25,
        "cookie_days": 60,
        "confidence": 0.9,
    }
    extras: dict = {"facts": facts, "category_epc": 0.5}
    if operator is not None:
        extras["epc_operator"] = operator
    prog = make_program(name="Acme Helpdesk", status="proposed", extras=extras)
    if clicks > 0:
        _metric(db, prog.id, clicks=clicks, revenue_approved_cents=40_000)
    return prog


def test_rescore_prefers_own_epc_then_operator_then_declared(
    db_session, make_program
):
    own_prog = _program_with_operator_epc(
        db_session, make_program, operator=0.1, clicks=200
    )
    op_prog = make_program(
        name="Operator Program",
        status="proposed",
        extras={
            "facts": {
                "program_name": "Operator Program",
                "commission_type": "percent_one_time",
                "commission_value": 10,
                "cookie_days": 30,
                "confidence": 0.8,
            },
            "epc_operator": 1.2,
        },
    )
    decl_prog = make_program(
        name="Declared Program",
        status="proposed",
        extras={
            "facts": {
                "program_name": "Declared Program",
                "commission_type": "percent_one_time",
                "commission_value": 15,
                "cookie_days": 30,
                "confidence": 0.8,
            },
        },
    )

    updated = rescore_proposed(db_session)
    db_session.commit()
    db_session.refresh(own_prog)
    db_session.refresh(op_prog)
    db_session.refresh(decl_prog)

    assert updated == 3
    assert own_prog.extras["epc_source"] == "own"
    assert own_prog.extras["score_breakdown"]["epc_source"] == "own"
    assert own_prog.extras["epc"] > 0.1

    assert op_prog.extras["epc_source"] == "operator"
    assert op_prog.extras["score_breakdown"]["epc_source"] == "operator"
    assert op_prog.extras["epc"] == 1.2

    assert decl_prog.extras["epc_source"] == "declared"
    assert decl_prog.extras["score_breakdown"]["epc_source"] == "declared"


def test_networks_fetch_performance(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr(config, "AWIN_PUBLISHER_ID", "999")
    monkeypatch.setattr(config, "AWIN_API_TOKEN", "awin-tok")
    monkeypatch.setattr(config, "IMPACT_ACCOUNT_SID", "imp-sid")
    monkeypatch.setattr(config, "IMPACT_AUTH_TOKEN", "imp-tok")
    monkeypatch.setattr(config, "CJ_API_KEY", "cj-key")

    def awin_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "date": "2026-10-05",
                    "advertiserId": 1234,
                    "clickRef": "abc123",
                    "clicks": 42,
                    "pendingNo": 2,
                    "approvedNo": 5,
                    "declinedNo": 1,
                    "pendingValue": 12.5,
                    "approvedValue": 75.0,
                    "currency": "EUR",
                }
            ],
        )

    awin_rows = AwinNetwork(
        transport=httpx.MockTransport(awin_handler)
    ).fetch_performance(date(2026, 10, 1), date(2026, 10, 7))
    assert len(awin_rows) == 1
    assert awin_rows[0].program_id == "1234"
    assert awin_rows[0].subid == "abc123"
    assert awin_rows[0].clicks == 42
    assert awin_rows[0].conversions_pending == 2
    assert awin_rows[0].conversions_approved == 5
    assert awin_rows[0].conversions_declined == 1
    assert awin_rows[0].revenue_pending_cents == 1250
    assert awin_rows[0].revenue_approved_cents == 7500
    assert awin_rows[0].currency == "EUR"

    def impact_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Records": [
                    {
                        "Date": "2026-10-06",
                        "CampaignId": "555",
                        "subId1": "subimp",
                        "Clicks": 15,
                        "PendingActions": 1,
                        "Actions": 3,
                        "ReversedActions": 0,
                        "PendingPayout": "10.00",
                        "Payout": "45.50",
                        "Currency": "USD",
                    }
                ]
            },
        )

    imp_rows = ImpactNetwork(
        transport=httpx.MockTransport(impact_handler)
    ).fetch_performance(date(2026, 10, 1), date(2026, 10, 7))
    assert len(imp_rows) == 1
    assert imp_rows[0].program_id == "555"
    assert imp_rows[0].subid == "subimp"
    assert imp_rows[0].revenue_approved_cents == 4550

    def cj_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "records": [
                    {
                        "date": "2026-10-06",
                        "programId": "777",
                        "sid": "subcj",
                        "clicks": 8,
                        "approvedNo": 1,
                        "approvedValue": 20.0,
                    }
                ]
            },
        )

    cj_rows = CjNetwork(
        transport=httpx.MockTransport(cj_handler)
    ).fetch_performance(date(2026, 10, 1), date(2026, 10, 7))
    assert len(cj_rows) == 1
    assert cj_rows[0].program_id == "777"
    assert cj_rows[0].revenue_approved_cents == 2000

    assert (
        ManualNetwork().fetch_performance(date(2026, 10, 1), date(2026, 10, 7))
        == []
    )
    assert (
        AmazonNetwork().fetch_performance(date(2026, 10, 1), date(2026, 10, 7))
        == []
    )


def test_sync_performance_writes_rows(db_session, make_program, monkeypatch):
    prog = make_program(network="awin", network_program_id="987")

    class _FakeNet:
        name = "awin"
        allow_redirect = True

        def fetch_performance(self, _since, _until):
            return [
                _performance(
                    day=date(2026, 10, 10),
                    program_id="987",
                    subid="sub99",
                    clicks=55,
                    conversions_approved=4,
                    revenue_approved_cents=8000,
                )
            ]

    monkeypatch.setattr(
        "research_agent.tasks.active_networks", lambda: [_FakeNet()]
    )
    res = sync_performance(db_session, days_back=7)
    assert res == {"rows": 1}
    stored = db_session.scalars(select(AffiliateMetric)).all()
    assert len(stored) == 1
    assert stored[0].program_id == prog.id
    assert stored[0].clicks == 55
    assert stored[0].revenue_approved_cents == 8000

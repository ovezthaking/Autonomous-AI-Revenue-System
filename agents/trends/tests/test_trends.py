"""Trends agent tests: IP filter, scoring, and idea proposals."""

import pytest
from revenue_swarm.enums import IdeaStatus
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy import select
from trends_agent.ip_filter import ip_risk
from trends_agent.score import features_for, score_idea
from trends_agent.tasks import collect_task, propose_task


def test_score_matches_breakdown():
    features = {
        "own_fit": 1.0,
        "demand": 0.5,
        "producibility": 1.0,
        "competition": 0.0,
    }
    total, breakdown = score_idea(features)
    assert total == round(sum(breakdown.values()), 4)


def test_denylist_blocks():
    assert ip_risk("Taylor Swift eras planner") == "denylist"
    assert ip_risk("Stanley cup habit tracker") == "denylist"
    assert ip_risk("monthly budget planner") is None


def test_none_from_model_blocks(monkeypatch):
    monkeypatch.setattr(
        "trends_agent.ip_filter.structured", lambda *a, **k: None
    )
    assert ip_risk("budget planner") == "possible trademark"


@pytest.mark.integration
def test_producibility_zero_rejects_and_blocked_never_proposed(
    db, monkeypatch
):
    monkeypatch.setattr("trends_agent.tasks.TRENDS_ENABLED", True)

    db.add_all(
        [
            TrendSignal(
                source="search",
                term="video editing software course",
                value=80.0,
                window_days=30,
            ),
            TrendSignal(
                source="search",
                term="Taylor Swift tour planner",
                value=95.0,
                window_days=30,
            ),
            TrendSignal(
                source="own",
                term="freelance tax checklist printable",
                value=100.0,
                window_days=90,
            ),
        ]
    )
    db.commit()

    assert (
        features_for(db, "video editing software course")["producibility"]
        == 0.0
    )

    result = propose_task()
    assert result == {"proposed": 1}

    ideas = list(db.scalars(select(ProductIdea)).all())
    by_term = {row.term: row for row in ideas}

    # Non-printable term is ignored completely
    assert "video editing software course" not in by_term

    # Trademark term is recorded as BLOCKED, never PROPOSED
    blocked = by_term["Taylor Swift tour planner"]
    assert blocked.status == IdeaStatus.BLOCKED.value
    assert blocked.blocked_reason == "denylist"

    # Valid printable term is PROPOSED with deterministic breakdown
    proposed = by_term["freelance tax checklist printable"]
    assert proposed.status == IdeaStatus.PROPOSED.value
    assert proposed.score > 0
    assert proposed.score == round(sum(proposed.score_breakdown.values()), 4)

    # Re-running propose_task does not duplicate existing ideas
    second = propose_task()
    assert second == {"proposed": 0}


@pytest.mark.integration
def test_collect_task_writes_signals_from_active_sources(
    db, monkeypatch, make_content_item
):
    monkeypatch.setattr("trends_agent.tasks.TRENDS_ENABLED", True)
    item = make_content_item(title="Home Budget Guide")
    from datetime import date

    from revenue_swarm.models.affiliate_metric import AffiliateMetric

    db.add(
        AffiliateMetric(
            network="awin",
            subid=item.id.hex,
            day=date(2026, 10, 1),
            clicks=10,
            conversions_approved=2,
            revenue_approved_cents=4500,
        )
    )
    db.commit()

    res = collect_task()
    assert res["signals"] >= 1
    own_sig = db.scalar(select(TrendSignal).where(TrendSignal.source == "own"))
    assert own_sig is not None
    assert own_sig.value == 4500.0
    assert "printable" in own_sig.term.lower()


@pytest.mark.integration
def test_trends_sources_scoring_and_edge_cases(
    db, monkeypatch, make_content_item
):
    from datetime import date
    from unittest.mock import MagicMock

    import trends_agent.worker as worker_mod
    from revenue_swarm import config
    from revenue_swarm.enums import OrderStatus, ProductStatus
    from revenue_swarm.models.affiliate_metric import AffiliateMetric
    from revenue_swarm.models.order import Order
    from revenue_swarm.models.product import Product
    from trends_agent.ip_filter import IpVerdict, structured as ip_structured
    from trends_agent.score import _demand, _own_fit
    from trends_agent.sources.gsc import GscSource
    from trends_agent.sources.orders import OrdersSource
    from trends_agent.sources.own import OwnSource, _normalize_printable_term
    from trends_agent.sources.search import _search_result_count

    assert worker_mod.celery_app is not None

    # 1. ip_filter non-stub path
    monkeypatch.setattr(config, "LLM_STUB", False)
    monkeypatch.setattr(
        "trends_agent.ip_filter.shared_llm.structured",
        lambda _p, _s: IpVerdict(mentions_brand_or_person=False),
    )
    assert ip_structured("p", IpVerdict).mentions_brand_or_person is False

    # 2. score.py: _own_fit via ContentItem (empty + matching with rev > 0)
    make_content_item(title="   ")
    ci_zero = make_content_item(title="Zero Rev Topic")
    ci_pos = make_content_item(title="Tax Checklist")
    db.add(
        AffiliateMetric(
            network="awin",
            subid=ci_pos.id.hex,
            day=date(2026, 10, 2),
            clicks=5,
            conversions_approved=1,
            revenue_approved_cents=1200,
        )
    )
    db.commit()
    assert _own_fit(db, "zero rev topic guide") == 0.0
    assert _own_fit(db, "freelance tax checklist") == 1.0
    assert ci_zero.id is not None

    # _demand branches: missing signal, value <= 1.0
    assert _demand(db, "nonexistent term") == 0.0
    db.add(
        TrendSignal(
            source="own", term="small demand term", value=0.45, window_days=30
        )
    )
    db.commit()
    assert _demand(db, "small demand term") == 0.45

    # 3. GscSource, OrdersSource, OwnSource branches
    gsc = GscSource()
    monkeypatch.setattr(config, "GSC_SITE_URL", "")
    assert gsc.collect(db) == []
    monkeypatch.setattr(config, "GSC_SITE_URL", "https://example.com")
    monkeypatch.setattr(config, "GSC_CREDENTIALS_JSON", "{}")
    assert gsc.collect(db) == []

    assert _normalize_printable_term("Daily Planner") == "Daily Planner"
    own_signals = OwnSource().collect(db)
    assert len(own_signals) == 1

    prod = Product(
        slug="trends-order-prod",
        title="Habit Tracker Printable",
        price_cents=1000,
        status=ProductStatus.LIVE.value,
    )
    db.add(prod)
    db.commit()
    db.add(
        Order(
            product_id=prod.id,
            provider="fake",
            provider_session_id="s_ord_1",
            amount_cents=1000,
            currency="USD",
            status=OrderStatus.FULFILLED.value,
        )
    )
    db.commit()
    order_signals = OrdersSource().collect(db)
    assert len(order_signals) == 1
    assert order_signals[0].term == "Habit Tracker Printable"

    # OrdersSource when db.get returns None
    monkeypatch.setattr(db, "get", lambda *_a, **_kw: None)
    assert OrdersSource().collect(db) == []

    # 4. search.py _search_result_count branches
    monkeypatch.setenv("SEARCH_STUB", "0")
    monkeypatch.setenv("SEARCH_API_KEY", "")
    assert _search_result_count("q") == 5

    monkeypatch.setenv("SEARCH_API_KEY", "key123")
    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"results": [1, 2, 3]}
    monkeypatch.setattr(
        "trends_agent.sources.search.httpx.post", lambda *_a, **_kw: fake_resp
    )
    assert _search_result_count("q") == 3

    monkeypatch.setenv("SEARCH_PROVIDER", "brave")
    fake_resp.json.return_value = {"web": {"results": [1, 2]}}
    monkeypatch.setattr(
        "trends_agent.sources.search.httpx.get", lambda *_a, **_kw: fake_resp
    )
    assert _search_result_count("q") == 2

    monkeypatch.setenv("SEARCH_PROVIDER", "other")
    assert _search_result_count("q") == 5

    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr(
        "trends_agent.sources.search.httpx.post",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    assert _search_result_count("q") == 10

    # 5. tasks.py disabled and max ideas per run + duplicate/blank terms
    monkeypatch.setattr("trends_agent.tasks.TRENDS_ENABLED", False)
    monkeypatch.setattr(config, "TRENDS_ENABLED", False)
    assert collect_task() == {"signals": 0}
    assert propose_task() == {"proposed": 0}

    monkeypatch.setattr("trends_agent.tasks.TRENDS_ENABLED", True)
    monkeypatch.setattr("trends_agent.tasks.TRENDS_MAX_IDEAS_PER_RUN", 0)
    db.add_all(
        [
            TrendSignal(source="own", term="   ", value=10.0, window_days=30),
            TrendSignal(
                source="own", term="dup planner", value=10.0, window_days=30
            ),
            TrendSignal(
                source="search", term="DUP PLANNER", value=20.0, window_days=30
            ),
        ]
    )
    db.commit()
    assert propose_task() == {"proposed": 0}

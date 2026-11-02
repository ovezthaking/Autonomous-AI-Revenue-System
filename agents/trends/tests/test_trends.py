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

"""Search demand signal source for printable product phrases."""

import os

import httpx
from revenue_swarm.models.trend_signal import TrendSignal
from sqlalchemy import select
from sqlalchemy.orm import Session

DEFAULT_SEEDS = (
    "monthly budget planner printable",
    "weekly habit tracker printable",
    "small business tax preparation checklist",
)


def _search_result_count(query: str) -> int:
    if os.getenv("SEARCH_STUB", "1") == "1":
        return 5
    provider = os.getenv("SEARCH_PROVIDER", "tavily").strip().lower()
    api_key = os.getenv("SEARCH_API_KEY", "") or ""
    if not api_key:
        return 5
    try:
        if provider == "tavily":
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": 10},
                timeout=15.0,
            )
            resp.raise_for_status()
            return len(resp.json().get("results") or [])
        if provider == "brave":
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 10},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return len((resp.json().get("web") or {}).get("results") or [])
    except Exception:
        return 10
    return 5


class SearchSource:
    name = "search"

    def collect(self, db: Session) -> list[TrendSignal]:
        own_terms = list(
            db.scalars(
                select(TrendSignal.term)
                .where(TrendSignal.source == "own")
                .limit(10)
            ).all()
        )
        candidates = list(dict.fromkeys([*own_terms, *DEFAULT_SEEDS]))
        signals: list[TrendSignal] = []
        for phrase in candidates:
            term = (
                phrase
                if "printable" in phrase.lower()
                else f"{phrase} printable"
            )
            count = _search_result_count(term)
            signals.append(
                TrendSignal(
                    source=self.name,
                    term=term,
                    value=float(max(count * 10, 10)),
                    window_days=30,
                    raw={"result_count": count},
                )
            )
        return signals

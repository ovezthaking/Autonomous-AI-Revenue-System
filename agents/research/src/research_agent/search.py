from collections.abc import Callable

import httpx

from research_agent.models import SearchHit
from research_agent.polite import send
from research_agent.settings import (
    SEARCH_API_KEY,
    SEARCH_MAX_RESULTS,
    SEARCH_PROVIDER,
    SEARCH_STUB,
)

QUERY_TEMPLATES = (
    "{niche} affiliate program commission",
    "{niche} partner program recurring commission",
    "best {niche} affiliate programs high ticket",
)

STUB_HITS = (
    SearchHit(
        url="https://vendor-a.test/affiliate-program",
        title="Vendor A Affiliate Program",
        snippet="Earn 25% recurring commission, 90-day cookie.",
        raw_content=(
            "Vendor A Affiliate Program. Earn 25% recurring commission "
            "for every paying customer. 90-day cookie window. Payouts "
            "from $50 via PayPal. Managed directly, no network."
        ),
    ),
    SearchHit(
        url="https://vendor-b.test/partners",
        title="Vendor B Partner Program",
        snippet="Earn 25% one-time commission, 30-day cookie.",
        raw_content=(
            "Vendor B Partner Program. Earn 25% one-time commission "
            "on the first purchase only. 30-day cookie window. Payouts "
            "from $100 via PayPal. Network: Impact."
        ),
    ),
    SearchHit(
        url="https://vendor-c.test/affiliates",
        title="Vendor C Affiliate Program",
        snippet="Flat $150 one-time bounty, 60-day cookie.",
        raw_content=(
            "Vendor C Affiliate Program. Earn a flat $150 one-time "
            "bounty per qualified signup. 60-day cookie window. Payouts "
            "from $25. Network: ShareASale. Currency: USD."
        ),
    ),
    SearchHit(
        url="https://roundup.test/best-affiliate-programs",
        title="Best affiliate programs roundup",
        snippet="A list of popular tools, with no commission terms.",
        raw_content=(
            "Best affiliate programs roundup. This page lists popular "
            "tools for small businesses. It does not state commission "
            "rates, cookie windows, payout thresholds, or a network."
        ),
    ),
)


def queries(niche: str) -> list[str]:
    return [template.format(niche=niche) for template in QUERY_TEMPLATES]


def search(niche: str) -> list[SearchHit]:
    if SEARCH_STUB:
        return list(STUB_HITS)
    if SEARCH_PROVIDER.strip().lower() == "tavily":
        return _tavily(queries(niche))
    if SEARCH_PROVIDER.strip().lower() == "brave":
        return _brave(queries(niche))
    msg = f"Unknown SEARCH_PROVIDER: {SEARCH_PROVIDER}"
    raise ValueError(msg)


def _collect(
    all_queries: list[str],
    fetch: Callable[[httpx.Client, str], list[SearchHit]],
) -> list[SearchHit]:
    hits: dict[str, SearchHit] = {}
    with httpx.Client(timeout=30.0) as client:
        for query in all_queries:
            for hit in fetch(client, query):
                hits.setdefault(hit.url, hit)
    return list(hits.values())


def _tavily_hits(client: httpx.Client, query: str) -> list[SearchHit]:
    response = send(
        "https://api.tavily.com/search",
        lambda: client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": SEARCH_API_KEY,
                "query": query,
                "max_results": SEARCH_MAX_RESULTS,
                "include_raw_content": True,
            },
        ),
    )
    response.raise_for_status()
    return [
        SearchHit(
            url=item["url"],
            title=item.get("title", ""),
            snippet=item.get("content", ""),
            raw_content=item.get("raw_content"),
        )
        for item in response.json().get("results", [])
    ]


def _brave_hits(client: httpx.Client, query: str) -> list[SearchHit]:
    response = send(
        "https://api.search.brave.com/res/v1/web/search",
        lambda: client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": SEARCH_MAX_RESULTS},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": SEARCH_API_KEY,
            },
        ),
    )
    response.raise_for_status()
    web = response.json().get("web") or {}
    return [
        SearchHit(
            url=item["url"],
            title=item.get("title", ""),
            snippet=item.get("description", ""),
            raw_content=None,
        )
        for item in web.get("results", [])
    ]


def _tavily(all_queries: list[str]) -> list[SearchHit]:
    return _collect(all_queries, _tavily_hits)


def _brave(all_queries: list[str]) -> list[SearchHit]:
    return _collect(all_queries, _brave_hits)

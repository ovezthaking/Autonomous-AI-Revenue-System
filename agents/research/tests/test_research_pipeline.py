import json
from pathlib import Path
from typing import cast

import httpx
import research_agent.extract as extract_module
import research_agent.search as search_module
from research_agent.agent import _drop_known, _normalize
from research_agent.models import ProgramFacts, SearchHit
from research_agent.score import score_program
from research_agent.search import (
    QUERY_TEMPLATES,
    STUB_HITS,
    queries,
    search,
)
from research_agent.validate import is_usable
from sqlalchemy.orm import Session

_ORIGINAL_SEND = httpx.Client.send
_FIXTURES = Path(__file__).parent / "fixtures"


def _facts(**overrides: object) -> ProgramFacts:
    payload = {
        "program_name": "Vendor",
        "commission_type": "percent_recurring",
        "commission_value": 25,
        "cookie_days": 90,
        "confidence": 0.9,
    }
    payload.update(overrides)
    return ProgramFacts.model_validate(payload)


def test_score_recurring_beats_same_percent_one_time():
    recurring, _ = score_program(_facts())
    one_time, _ = score_program(_facts(commission_type="percent_one_time"))
    assert recurring > one_time


def test_score_missing_commission_value_does_not_raise():
    score, breakdown = score_program(_facts(commission_value=None))
    assert score >= 0
    assert "commission" in breakdown


def test_score_epc_reorders_programs():
    strong = _facts(cookie_days=0, confidence=0)
    weak = _facts(
        commission_type="percent_one_time",
        commission_value=10,
        cookie_days=0,
        confidence=0,
    )
    assert score_program(strong)[0] > score_program(weak)[0]
    assert score_program(weak, epc=3)[0] > score_program(strong)[0]


def test_score_breakdown_sums_to_score():
    score, breakdown = score_program(
        _facts(commission_value=25, cookie_days=30, confidence=0.4)
    )
    assert round(sum(breakdown.values()), 2) == score


def test_is_usable_rejects_low_confidence_unknown_type_and_limits():
    assert not is_usable(_facts(confidence=0.2), "https://vendor.test/a")
    assert not is_usable(
        _facts(commission_type="mystery"), "https://vendor.test/a"
    )
    assert not is_usable(_facts(commission_value=101), "https://vendor.test/a")
    assert not is_usable(_facts(cookie_days=5000), "https://vendor.test/a")
    assert not is_usable(_facts(), "https://www.reddit.com/r/affiliates")


def test_normalize_treats_case_and_spacing_as_the_same_name():
    assert _normalize("Vendor  A") == _normalize("vendor a")

    class _Rows:
        def all(self):
            return [("Vendor A", "https://kept.test/old")]

    class _DB:
        def execute(self, _stmt):
            return _Rows()

    from research_agent.models import Candidate

    fresh = _drop_known(
        cast(Session, _DB()),
        [
            Candidate(
                name="vendor  a",
                url="https://other.test/new",
                evidence_url="https://other.test/new",
                facts=_facts(program_name="vendor  a"),
            )
        ],
    )
    assert fresh == []


def test_queries_include_the_niche():
    result = queries("CRM")
    assert len(result) == len(QUERY_TEMPLATES)
    assert all("CRM" in query for query in result)


def test_search_stub_returns_hits_without_http(monkeypatch):
    monkeypatch.setattr(search_module, "SEARCH_STUB", True)

    def _boom(*args, **kwargs):
        raise AssertionError("HTTP client created")

    monkeypatch.setattr(search_module.httpx, "Client", _boom)
    assert search("saas") == list(STUB_HITS)


def test_tavily_maps_fields_and_dedups_urls(monkeypatch):
    monkeypatch.setattr(httpx.Client, "send", _ORIGINAL_SEND)
    monkeypatch.setattr("research_agent.polite.REQUEST_GAP_SECONDS", 0)
    monkeypatch.setattr(search_module, "SEARCH_STUB", False)
    payload = json.loads((_FIXTURES / "tavily_search.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    class _Client(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(search_module.httpx, "Client", _Client)
    hits = search_module._tavily(["first query", "second query"])
    assert [hit.url for hit in hits] == [
        "https://vendor-a.test/affiliate-program",
        "https://vendor-b.test/partners",
    ]
    assert hits[0].title == "Vendor A"
    assert hits[0].snippet == "snippet a"
    assert hits[0].raw_content == "raw a"


def test_extract_facts_returns_none_when_structured_fails(monkeypatch):
    monkeypatch.setattr(extract_module, "LLM_STUB", False)
    monkeypatch.setattr(
        extract_module, "structured", lambda prompt, schema: None
    )
    hit = SearchHit(url="https://vendor.test/a", title="Vendor")
    assert extract_module.extract_facts(hit, "page text") is None


def test_extract_facts_maps_loose_commission_labels(monkeypatch):
    monkeypatch.setattr(extract_module, "LLM_STUB", False)
    seen: dict[str, str] = {}

    def _structured(prompt, schema):
        seen["type"] = prompt
        return ProgramFacts(
            program_name="Vendor",
            commission_type="recurring",
            commission_value=25,
            confidence=0.9,
        )

    monkeypatch.setattr(extract_module, "structured", _structured)
    hit = SearchHit(url="https://vendor.test/a", title="Vendor")
    facts = extract_module.extract_facts(hit, "25% recurring")
    assert facts is not None
    assert facts.commission_type == "percent_recurring"
    assert "percent_one_time" in seen["type"]
    assert "flat_one_time" in seen["type"]

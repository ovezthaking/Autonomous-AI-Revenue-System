import json
import uuid
from pathlib import Path
from typing import cast

import httpx
import research_agent.agent as agent_module
import research_agent.extract as extract_module
import research_agent.search as search_module
from research_agent.agent import _drop_known, _normalize, discover_programs_v2
from research_agent.models import ProgramFacts, SearchHit
from research_agent.score import score_program
from research_agent.search import (
    QUERY_TEMPLATES,
    STUB_HITS,
    queries,
    search,
)
from research_agent.validate import is_usable, looks_like_program_url
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
    assert not is_usable(_facts(), "https://en.wikipedia.org/wiki/Best")
    assert not is_usable(_facts(), "https://www.thefreedictionary.com/best")
    assert not is_usable(
        _facts(), "https://www.businessofapps.com/affiliate/ecommerce"
    )
    assert not is_usable(
        _facts(),
        "https://sparkreceipt.com/blog/best-recurring-commission-affiliate-programs",
    )
    assert not is_usable(
        _facts(),
        "https://partnerstack.com/articles/top-paying-affiliate-programs",
    )
    assert not is_usable(
        _facts(),
        "https://xamplify.com/guides/best-msp-partner-program-software",
    )
    assert is_usable(_facts(), "https://vendor.test/affiliate-program")


def test_only_program_paths_are_sent_on_for_extraction():
    assert looks_like_program_url(
        "https://www.liveagent.com/affiliate-program"
    )
    assert looks_like_program_url("https://www.bolddesk.com/affiliate-program")
    assert looks_like_program_url(
        "https://pipelinecrm.com/partners/affiliates"
    )
    assert not looks_like_program_url("https://example.com/blog/best-programs")
    assert not looks_like_program_url(
        "https://profitbooks.net/highest-paying-affiliate-marketing-programs"
    )
    assert not looks_like_program_url(
        "https://smallbusiness.management/affiliate-marketing-small-business"
    )
    assert not looks_like_program_url("https://vendor.test/")
    assert not looks_like_program_url(
        "https://affiliate.watch/affiliate/helpdesk"
    )
    assert not is_usable(
        _facts(),
        "https://profitbooks.net/highest-paying-affiliate-marketing-programs",
    )


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


def test_drop_known_treats_www_as_the_same_host():
    class _Rows:
        def all(self):
            return [
                ("LiveAgent", "https://www.liveagent.com/affiliate-program")
            ]

    class _DB:
        def execute(self, _stmt):
            return _Rows()

    from research_agent.models import Candidate

    fresh = _drop_known(
        cast(Session, _DB()),
        [
            Candidate(
                name="LiveAgent Affiliate",
                url="https://liveagent.com/affiliate-program",
                evidence_url="https://liveagent.com/affiliate-program",
                facts=_facts(program_name="LiveAgent Affiliate"),
            )
        ],
    )
    assert fresh == []


def test_queries_include_the_niche():
    result = queries("CRM")
    assert len(result) == len(QUERY_TEMPLATES)
    assert all("CRM" in query for query in result)
    assert all("best " not in query.lower() for query in result)


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

    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
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
    assert bodies[0]["search_depth"] == "advanced"
    excluded = bodies[0]["exclude_domains"]
    assert isinstance(excluded, list)
    assert "lemlist.com" in excluded


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
    assert "payout_threshold" in seen["type"]


def test_extract_sends_terms_instead_of_the_page_menu(monkeypatch):
    monkeypatch.setattr(extract_module, "LLM_STUB", False)
    seen: dict[str, str] = {}

    def _structured(prompt, _schema):
        seen["prompt"] = prompt
        return ProgramFacts(
            program_name="LiveAgent",
            commission_type="percent_recurring",
            commission_value=30,
            confidence=0.9,
        )

    monkeypatch.setattr(extract_module, "structured", _structured)
    nav = "Open main menu " * 2000
    terms = (
        "Earn up to 30% commission for each recurring payment. "
        "90 day cookie. minimum payout of $250."
    )
    extract_module.extract_facts(
        SearchHit(
            url="https://www.liveagent.com/affiliate-program",
            title="LiveAgent",
        ),
        nav + terms,
    )
    assert "30% commission" in seen["prompt"]
    assert seen["prompt"].count("Open main menu") < 40


def test_extract_keeps_only_a_payout_written_on_the_page(monkeypatch):
    monkeypatch.setattr(extract_module, "LLM_STUB", False)

    def _structured(_prompt, _schema):
        return ProgramFacts(
            program_name="Affiliate Partnership",
            commission_type="percent_one_time",
            commission_value=5,
            payout_threshold=50_000,
            confidence=0.9,
        )

    monkeypatch.setattr(extract_module, "structured", _structured)
    hit = SearchHit(
        url="https://help-desk-migration.com/partners",
        title="Help Desk Migration Partner Program",
    )
    text = (
        "Earn 5% commission on new referral clients. "
        "Refer customers with migrations over $50K."
    )
    facts = extract_module.extract_facts(hit, text)
    assert facts is not None
    assert facts.payout_threshold is None
    assert facts.program_name == "Help Desk Migration Partner Program"

    def _stated(_prompt, _schema):
        return ProgramFacts(
            program_name="LiveAgent",
            commission_type="percent_recurring",
            commission_value=30,
            payout_threshold=250,
            confidence=0.9,
        )

    monkeypatch.setattr(extract_module, "structured", _stated)
    stated = extract_module.extract_facts(
        SearchHit(
            url="https://liveagent.com/affiliate-program",
            title="LiveAgent",
        ),
        "Two referrals are required for a minimum payout of $250.",
    )
    assert stated is not None
    assert stated.payout_threshold == 250


def test_extract_fills_a_cookie_window_the_model_skipped(monkeypatch):
    monkeypatch.setattr(extract_module, "LLM_STUB", False)

    def _structured(_prompt, _schema):
        return ProgramFacts(
            program_name="LiveAgent",
            commission_type="percent_recurring",
            commission_value=30,
            cookie_days=None,
            confidence=0.9,
        )

    monkeypatch.setattr(extract_module, "structured", _structured)
    facts = extract_module.extract_facts(
        SearchHit(
            url="https://www.liveagent.com/affiliate-program",
            title="LiveAgent",
        ),
        "Earn 30% commission. The cookie window to 90 days.",
    )
    assert facts is not None
    assert facts.cookie_days == 90


def test_discover_reads_the_fetched_page_before_search_content(monkeypatch):
    monkeypatch.setattr(
        agent_module,
        "search",
        lambda _niche: [
            SearchHit(
                url="https://www.liveagent.com/affiliate-program",
                title="LiveAgent",
                raw_content="Search snippet without terms.",
            )
        ],
    )
    monkeypatch.setattr(
        agent_module,
        "fetch_text",
        lambda _url: "Earn 30% recurring commission. 90-day cookie.",
    )
    seen: dict[str, str] = {}

    def _extract(_hit, text):
        seen["text"] = text
        return None

    monkeypatch.setattr(agent_module, "extract_facts", _extract)

    class _Rows:
        def all(self):
            return []

    class _DB:
        def execute(self, _stmt):
            return _Rows()

        def commit(self):
            return None

    discover_programs_v2(cast(Session, _DB()), uuid.uuid4())
    assert "30% recurring commission" in seen["text"]


def test_discover_rejects_a_blocked_url_without_calling_the_model(monkeypatch):
    monkeypatch.setattr(
        agent_module,
        "search",
        lambda _niche: [
            SearchHit(
                url="https://vendor.test/pricing",
                title="List",
                raw_content="Earn 25% recurring commission. 90-day cookie.",
            )
        ],
    )

    def _boom(_hit, _text):
        raise AssertionError("model was called")

    monkeypatch.setattr(agent_module, "extract_facts", _boom)

    class _Rows:
        def all(self):
            return []

    class _DB:
        def execute(self, _stmt):
            return _Rows()

        def commit(self):
            return None

    result = discover_programs_v2(cast(Session, _DB()), uuid.uuid4())
    assert result["created"] == 0
    assert result["candidates"] == 0
    errors = result["errors"]
    assert isinstance(errors, list)
    assert errors[0]["error"] == "rejected"

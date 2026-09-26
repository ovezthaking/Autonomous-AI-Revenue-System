import revenue_swarm.llm as llm_module
from research_agent.agent import filter_new_candidates
from research_agent.catalog import CANDIDATES


def test_filter_skip_existing_names():
    existing = {CANDIDATES[0].name}
    result = filter_new_candidates(CANDIDATES, existing, limit=10)
    assert CANDIDATES[0] not in result
    assert len(result) == len(CANDIDATES) - 1


def test_filter_respects_limit():
    result = filter_new_candidates(CANDIDATES, set(), limit=2)
    assert len(result) == 2


def test_filter_returns_empty_when_everything_exists():
    existing = {c.name for c in CANDIDATES}
    assert filter_new_candidates(CANDIDATES, existing, limit=10) == []


def test_generate_rationale_returns_stub_when_enabled(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_STUB", True)
    assert llm_module.generate_rationale("x") == llm_module.STUB_RATIONALE

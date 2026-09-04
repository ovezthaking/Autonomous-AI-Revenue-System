"""
Tests for `generate_paragraph`. Zero DB, zero real network — the
LLM_STUB=1 branch is tested explicitly, and the "real" Ollama call branch
is tested by mocking httpx.Client.post.
"""

import app.services.llm as llm_module
import httpx
import pytest


def test_generate_paragraph_returns_stub_when_llm_stub_enabled(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_STUB", True)
    result = llm_module.generate_paragraph("any prompt")
    assert result == llm_module.STUB_TEXT


def test_generate_paragraph_calls_ollama_when_stub_disabled(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_STUB", False)
    monkeypatch.setattr(llm_module, "OLLAMA_BASE_URL", "http://ollama-test")
    monkeypatch.setattr(llm_module, "OLLAMA_MODEL", "llama3.2:1b")

    captured_calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "  Generated paragraph.  "}

    class FakeClient:
        def __init__(self, timeout=None):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def post(self, url, json):
            captured_calls.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    result = llm_module.generate_paragraph("Describe the architecture.")

    assert result == "Generated paragraph."
    assert len(captured_calls) == 1
    url, payload = captured_calls[0]
    assert url == "http://ollama-test/api/generate"
    assert payload == {
        "model": "llama3.2:1b",
        "prompt": "Describe the architecture.",
        "stream": False,
    }


def test_generate_paragraph_propagates_http_errors(monkeypatch):
    monkeypatch.setattr(llm_module, "LLM_STUB", False)
    monkeypatch.setattr(llm_module, "OLLAMA_BASE_URL", "http://ollama-test")

    class FailingResponse:
        def raise_for_status(self):
            request = httpx.Request("POST", "http://ollama-test/api/generate")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError(
                "boom", request=request, response=response
            )

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def post(self, url, json):
            return FailingResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    with pytest.raises(httpx.HTTPStatusError):
        llm_module.generate_paragraph("prompt")

"""
Tests for `generate_paragraph`. Zero DB, zero real network — the
LLM_STUB=1 branch is tested explicitly, and the "real" Ollama call branch
is tested by mocking httpx.Client.post.
"""

import httpx
import pytest
import revenue_swarm.llm as llm_module


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


def test_chat_and_rationale_and_copy(monkeypatch):
    from unittest.mock import MagicMock

    # Stub mode
    monkeypatch.setattr(llm_module, "LLM_STUB", True)
    assert llm_module.generate_rationale("p") == llm_module.STUB_RATIONALE
    assert llm_module.generate_copy("p", stub="custom-stub") == "custom-stub"

    # Non-stub mode
    monkeypatch.setattr(llm_module, "LLM_STUB", False)
    fake_msg = MagicMock()
    fake_msg.content = "  chat response  "
    fake_ollama = MagicMock()
    fake_ollama.invoke.return_value = fake_msg
    monkeypatch.setattr(llm_module, "ChatOllama", lambda **_kw: fake_ollama)

    assert llm_module.chat("hello", temperature=0.3) == "chat response"
    assert llm_module.generate_rationale("why?") == "chat response"
    assert llm_module.generate_copy("write", stub="s") == "chat response"


def test_chat_model_providers_structured_and_chat_with_usage(monkeypatch):
    from unittest.mock import MagicMock

    import langchain_anthropic
    import langchain_ollama
    from pydantic import BaseModel

    class SampleSchema(BaseModel):
        answer: str

    # 1. _chat_model with anthropic vs ollama
    fake_anthropic_cls = MagicMock(return_value="anthropic-instance")
    fake_ollama_cls = MagicMock(return_value="ollama-instance")
    monkeypatch.setattr(
        langchain_anthropic, "ChatAnthropic", fake_anthropic_cls
    )
    monkeypatch.setattr(langchain_ollama, "ChatOllama", fake_ollama_cls)

    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "anthropic")
    assert llm_module._chat_model(0.1) == "anthropic-instance"

    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "ollama")
    assert llm_module._chat_model(0.1) == "ollama-instance"

    # 2. structured: stub, valid schema, non-schema return, and exception
    monkeypatch.setattr(llm_module, "LLM_STUB", True)
    assert llm_module.structured("p", SampleSchema) is None

    monkeypatch.setattr(llm_module, "LLM_STUB", False)
    fake_structured_runner = MagicMock()
    fake_base_model = MagicMock()
    fake_base_model.with_structured_output.return_value = (
        fake_structured_runner
    )
    monkeypatch.setattr(
        llm_module, "_chat_model", lambda *_a, **_kw: fake_base_model
    )

    valid_obj = SampleSchema(answer="yes")
    fake_structured_runner.invoke.return_value = valid_obj
    assert llm_module.structured("p", SampleSchema) == valid_obj

    fake_structured_runner.invoke.return_value = {"not": "model"}
    assert llm_module.structured("p", SampleSchema) is None

    fake_structured_runner.invoke.side_effect = RuntimeError("parse error")
    assert llm_module.structured("p", SampleSchema) is None

    # 3. chat_with_usage: stub, explicit total_tokens, and fallback estimate
    monkeypatch.setattr(llm_module, "LLM_STUB", True)
    assert llm_module.chat_with_usage("p") == (llm_module.STUB_TEXT, 0)

    monkeypatch.setattr(llm_module, "LLM_STUB", False)
    msg_with_usage = MagicMock()
    msg_with_usage.content = "  hello world  "
    msg_with_usage.usage_metadata = {"total_tokens": 42}
    fake_base_model.invoke.return_value = msg_with_usage
    assert llm_module.chat_with_usage("prompt") == ("hello world", 42)

    msg_no_usage = MagicMock()
    msg_no_usage.content = "abcd"
    msg_no_usage.usage_metadata = {}
    fake_base_model.invoke.return_value = msg_no_usage
    text, tokens = llm_module.chat_with_usage("12345678")
    assert text == "abcd"
    assert tokens == (8 + 4) // 4

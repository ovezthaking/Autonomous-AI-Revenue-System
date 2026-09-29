import httpx
from langchain_ollama import ChatOllama
from pydantic import BaseModel, SecretStr

from revenue_swarm.config import (
    ANTHROPIC_API_KEY,
    LLM_PROVIDER,
    LLM_QUALITY_MODEL,
    LLM_STUB,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

STUB_TEXT = (
    "This is a stub paragraph. LLM_STUB=1; no model was called. "
    "The walking skeleton writes this string to Postgres."
)

STUB_RATIONALE = (
    "Stub rationale (LLM_STUB=1): recurring SaaS commission and a "
    "predictable payout profile; queued for human review."
)


def chat(prompt: str, temperature: float = 0.2) -> str:
    model = ChatOllama(
        model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=temperature
    )
    message = model.invoke(prompt)
    return str(message.content).strip()


def generate_paragraph(prompt: str) -> str:
    if LLM_STUB:
        return STUB_TEXT
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data.get("response", "")).strip()


def generate_rationale(prompt: str) -> str:
    if LLM_STUB:
        return STUB_RATIONALE
    return chat(prompt, temperature=0.2)


def generate_copy(prompt: str, *, stub: str) -> str:
    if LLM_STUB:
        return stub
    return chat(prompt, temperature=0.5)


def _chat_model(temperature: float = 0.0):
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=LLM_QUALITY_MODEL,
            api_key=SecretStr(ANTHROPIC_API_KEY),
            temperature=temperature,
            timeout=None,
            stop=None,
        )
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
    )


def structured[T: BaseModel](prompt: str, schema: type[T]) -> T | None:
    """Returns schema-validated output, or None when the model fails it."""
    if LLM_STUB:
        return None
    model = _chat_model().with_structured_output(schema)
    try:
        result = model.invoke(prompt)
    except Exception:
        return None
    if isinstance(result, schema):
        return result
    return None

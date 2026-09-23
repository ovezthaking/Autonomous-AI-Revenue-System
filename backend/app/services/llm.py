import httpx
from langchain_ollama import ChatOllama

from app.core.config import LLM_STUB, OLLAMA_BASE_URL, OLLAMA_MODEL

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

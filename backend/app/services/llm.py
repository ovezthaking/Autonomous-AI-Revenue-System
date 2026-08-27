import httpx

from app.core.config import LLM_STUB, OLLAMA_BASE_URL, OLLAMA_MODEL

STUB_TEXT = (
    "This is a stub paragraph. LLM_STUB=1; no model was called. "
    "The walking skeleton writes this string to Postgres."
)


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

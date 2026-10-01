import re

from revenue_swarm.config import LLM_STUB
from revenue_swarm.llm import structured

from research_agent.models import ProgramFacts, SearchHit

EXTRACT_PROMPT = (
    "Extract affiliate program terms from the page text below. "
    "Use null for anything the page does not state explicitly. "
    "Never guess numbers. Set confidence below 0.3 if the page does not "
    "clearly describe an affiliate or partner program.\n\n"
    "PAGE TEXT:\n{text}"
)

MAX_CHARS = 12_000


def _facts_from_stub(hit: SearchHit) -> ProgramFacts:
    text = hit.raw_content or ""
    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    flat = re.search(r"flat \$(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    cookie = re.search(r"(\d+)-day cookie", text, re.IGNORECASE)
    payout = re.search(r"Payouts from \$(\d+(?:\.\d+)?)", text)
    network_name = re.search(r"Network:\s*([A-Za-z]+)", text)
    lowered = text.lower()
    if "no network" in lowered or "managed directly" in lowered:
        network = "direct"
    elif network_name:
        network = network_name.group(1).lower()
    else:
        network = None
    if flat:
        commission_type = "flat_one_time"
        commission_value = float(flat.group(1))
    elif percent and "recurring" in lowered:
        commission_type = "percent_recurring"
        commission_value = float(percent.group(1))
    elif percent and "one-time" in lowered:
        commission_type = "percent_one_time"
        commission_value = float(percent.group(1))
    else:
        commission_type = "unknown"
        commission_value = None
    return ProgramFacts(
        program_name=hit.title or "Unknown",
        commission_type=commission_type,
        commission_value=commission_value,
        currency="USD" if "$" in text else None,
        cookie_days=int(cookie.group(1)) if cookie else None,
        payout_threshold=float(payout.group(1)) if payout else None,
        network=network,
        confidence=0.9 if commission_value is not None else 0.1,
    )


def extract_facts(hit: SearchHit, text: str) -> ProgramFacts | None:
    if LLM_STUB:
        return _facts_from_stub(hit)
    prompt = EXTRACT_PROMPT.format(text=text[:MAX_CHARS])
    return structured(prompt, ProgramFacts)

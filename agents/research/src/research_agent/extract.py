import re

from revenue_swarm.config import LLM_STUB
from revenue_swarm.llm import structured

from research_agent.models import ProgramFacts, SearchHit

EXTRACT_PROMPT = (
    "Extract affiliate program terms from the page text below. "
    "Use null for anything the page does not state explicitly. "
    "Never guess numbers.\n"
    "commission_type must be exactly one of these strings: "
    "percent_recurring, percent_one_time, flat_one_time, unknown.\n"
    "If the page states several commission percentages, use the highest.\n"
    "cookie_days is the cookie window in days. "
    "A 90 day cookie window means cookie_days is 90.\n"
    "payout_threshold is the minimum amount paid to the affiliate. "
    "Use null for a signup bonus or a customer spend tier.\n"
    "program_name is the company or product.\n"
    "Set confidence to 0.9 when the page states a commission.\n\n"
    "PAGE TITLE:\n{title}\n\n"
    "PAGE TEXT:\n{text}"
)

_COMMISSION_TYPES = {
    "percent_recurring": "percent_recurring",
    "recurring": "percent_recurring",
    "percent_one_time": "percent_one_time",
    "one-time": "percent_one_time",
    "one_time": "percent_one_time",
    "flat_one_time": "flat_one_time",
    "flat": "flat_one_time",
    "bounty": "flat_one_time",
    "unknown": "unknown",
}

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


def _relevant_text(text: str) -> str:
    start_at = text.lower().find("commission")
    if start_at == -1:
        return text[:MAX_CHARS]
    start = max(0, start_at - 100)
    return text[start : start + 4_000]


def extract_facts(hit: SearchHit, text: str) -> ProgramFacts | None:
    if LLM_STUB:
        return _facts_from_stub(hit)
    prompt = EXTRACT_PROMPT.format(title=hit.title, text=_relevant_text(text))
    facts = structured(prompt, ProgramFacts)
    if facts is None:
        return None
    return _align_with_page(hit, text, _canonicalize(facts))


_GENERIC_PROGRAM_NAMES = {
    "affiliate partnership",
    "affiliate program",
    "partner program",
    "partners",
}


def _align_with_page(
    hit: SearchHit, text: str, facts: ProgramFacts
) -> ProgramFacts:
    updates: dict[str, object] = {}
    name = facts.program_name.strip().lower()
    title = hit.title.strip()
    if name in _GENERIC_PROGRAM_NAMES and title:
        updates["program_name"] = title
    if facts.cookie_days is None:
        days = _stated_cookie_days(text)
        if days is not None:
            updates["cookie_days"] = days
    if facts.payout_threshold is not None and not _payout_is_on_page(
        text, facts.payout_threshold
    ):
        updates["payout_threshold"] = None
    if not updates:
        return facts
    return facts.model_copy(update=updates)


_COOKIE_DAYS = re.compile(
    r"(\d+)\s*-?\s*days?\s+cookie|"
    r"(\d+)\s*-?\s*days?\s+lifespan|"
    r"cookie(?:\s+window|\s+period|\s+lifespan)?"
    r"(?:\s+is\s+valid\s+for|\s+to|\s+of)?"
    r"\s+(\d+)\s+days",
    re.IGNORECASE,
)


def _stated_cookie_days(text: str) -> int | None:
    match = _COOKIE_DAYS.search(text)
    if match is None:
        return None
    days = int(next(group for group in match.groups() if group))
    if 0 < days <= 730:
        return days
    return None


def _payout_is_on_page(text: str, value: float) -> bool:
    amount = int(value) if value.is_integer() else value
    number = re.escape(str(amount))
    spaced = rf"(?<!\d){number}(?!\d)"
    ahead = re.compile(
        rf"(?:payout|minimum payment).{{0,40}}{spaced}",
        re.IGNORECASE | re.DOTALL,
    )
    behind = re.compile(
        rf"{spaced}.{{0,40}}(?:payout|minimum payment)",
        re.IGNORECASE | re.DOTALL,
    )
    return ahead.search(text) is not None or behind.search(text) is not None


def _canonicalize(facts: ProgramFacts) -> ProgramFacts:
    mapped = _COMMISSION_TYPES.get(facts.commission_type.strip().lower())
    if mapped is None or mapped == facts.commission_type:
        return facts
    return facts.model_copy(update={"commission_type": mapped})

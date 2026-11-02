"""Intellectual property and trademark filter run before idea scoring."""

from pathlib import Path

from pydantic import BaseModel
from revenue_swarm import config, llm as shared_llm

DENYLIST_PATH = Path(__file__).parent / "denylist.txt"

IP_PROMPT = (
    "Does this product phrase name a brand, trademark, or real person? "
    "Phrase: {term}"
)


class IpVerdict(BaseModel):
    mentions_brand_or_person: bool


def structured(prompt: str, schema: type[IpVerdict]) -> IpVerdict | None:
    if config.LLM_STUB:
        return IpVerdict(mentions_brand_or_person=False)
    return shared_llm.structured(prompt, schema)


def ip_risk(term: str) -> str | None:
    if _matches_denylist(term):
        return "denylist"
    verdict = structured(IP_PROMPT.format(term=term), IpVerdict)
    if verdict is None or verdict.mentions_brand_or_person:
        return "possible trademark"
    return None


def _matches_denylist(term: str) -> bool:
    lowered = term.lower()
    for line in DENYLIST_PATH.read_text(encoding="utf-8").splitlines():
        brand = line.strip().lower()
        if brand and brand in lowered:
            return True
    return False

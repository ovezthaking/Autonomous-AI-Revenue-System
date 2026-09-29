from research_agent.models import ProgramFacts

ALLOWED_TYPES = {
    "percent_recurring",
    "percent_one_time",
    "flat_one_time",
    "unknown",
}
BLOCKED_HOST_FRAGMENTS = ("reddit.", "quora.", "pinterest.", "youtube.")


def is_usable(facts: ProgramFacts, url: str) -> bool:
    if facts.confidence < 0.3:
        return False
    if facts.commission_type not in ALLOWED_TYPES:
        return False
    if facts.commission_type == "unknown" and facts.commission_value is None:
        return False
    if (
        facts.commission_value is not None
        and not 0 < facts.commission_value <= 100_00
    ):
        return False
    if facts.cookie_days is not None and not 0 < facts.cookie_days <= 730:
        return False
    if any(frag in url for frag in BLOCKED_HOST_FRAGMENTS):
        return False
    return True

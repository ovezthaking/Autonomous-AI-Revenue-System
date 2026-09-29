from research_agent.models import ProgramFacts

WEIGHTS = {
    "commission": 40.0,
    "recurring": 25.0,
    "cookie": 10.0,
    "confidence": 10.0,
    "epc": 60.0,
}


def score_program(
    facts: ProgramFacts, epc: float | None = None
) -> tuple[float, dict[str, float]]:
    parts: dict[str, float] = {}

    value = facts.commission_value or 0.0
    if facts.commission_type.startswith("percent"):
        parts["commission"] = min(value / 30.0, 1.0) * WEIGHTS["commission"]
    else:
        parts["commission"] = min(value / 200.0, 1.0) * WEIGHTS["commission"]

    parts["recurring"] = (
        WEIGHTS["recurring"]
        if facts.commission_type == "percent_recurring"
        else 0.0
    )
    parts["cookie"] = (
        min((facts.cookie_days or 0) / 90.0, 1.0) * WEIGHTS["cookie"]
    )
    parts["confidence"] = facts.confidence * WEIGHTS["confidence"]

    if epc is not None:
        parts["epc"] = min(epc / 3.0, 1.0) * WEIGHTS["epc"]

    return round(sum(parts.values()), 2), {
        k: round(v, 2) for k, v in parts.items()
    }

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    url: str
    title: str
    snippet: str = ""
    raw_content: str | None = None


class ProgramFacts(BaseModel):
    """Facts an LLM is allowed to extract from a program page"""

    program_name: str = Field(
        description="Company or product that pays the commission"
    )
    commission_type: str = Field(
        description="one of: percent_recurring, percent_one_time, "
        "flat_one_time, unknown"
    )
    commission_value: float | None = Field(
        default=None, description="Percent or amount; null if unknown"
    )
    currency: str | None = None
    cookie_days: int | None = None
    payout_threshold: float | None = Field(
        default=None,
        description="Minimum affiliate payout. Null if unstated, if there "
        "is no minimum, or if the number is a customer spend tier "
        "or a signup bonus",
    )
    network: str | None = Field(
        default=None, description="e.g. direct, impact, shareasale"
    )
    category: str | None = None
    confidence: float = Field(
        default=0.0, description="0-1, how clearly the page states the terms"
    )


class Candidate(BaseModel):
    name: str
    url: str
    evidence_url: str
    facts: ProgramFacts
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)

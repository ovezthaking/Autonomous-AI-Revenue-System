from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    url: str
    network: str
    category: str
    commission: str
    recurring: bool


CANDIDATES: tuple[Candidate, ...] = (
    Candidate(
        name="Example CRM Partner Program",
        url="https://example-crm.test/partners",
        network="direct",
        category="saas",
        commission="20% recurring",
        recurring=True,
    ),
    Candidate(
        name="Example Hosting Affiliates",
        url="https://example-hosting.test/affiliates",
        network="impact",
        category="high-ticket",
        commission="$150 per sale",
        recurring=False,
    ),
    Candidate(
        name="Example Analytics Referrals",
        url="https://example-analytics.test/referral",
        network="direct",
        category="saas",
        commission="25% recurring",
        recurring=True,
    ),
    Candidate(
        name="Example Course Platform",
        url="https://example-courses.test/affiliate",
        network="partnerstack",
        category="high-ticket",
        commission="30% first year",
        recurring=False,
    ),
    Candidate(
        name="Example Email Suite",
        url="https://example-email.test/partners",
        network="direct",
        category="saas",
        commission="30% recurring",
        recurring=True,
    ),
)

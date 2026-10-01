from urllib.parse import urlparse

from research_agent.models import ProgramFacts

ALLOWED_TYPES = {
    "percent_recurring",
    "percent_one_time",
    "flat_one_time",
    "unknown",
}
BLOCKED_HOST_FRAGMENTS = (
    "reddit.",
    "quora.",
    "pinterest.",
    "youtube.",
    "wikipedia.org",
    "thefreedictionary.com",
    "businessofapps.com",
    "affiliate.watch",
)
BLOCKED_PATH_FRAGMENTS = (
    "/blog/",
    "/blogs/",
    "/article/",
    "/articles/",
    "/guides/",
    "/wiki/",
    "best-",
    "highest-paying",
    "top-paying",
)
_PROGRAM_PARTS = {
    "affiliate",
    "affiliates",
    "affiliate-program",
    "partner-program",
    "partners",
}


def is_blocked_url(url: str) -> bool:
    if any(fragment in url for fragment in BLOCKED_HOST_FRAGMENTS):
        return True
    return any(fragment in url for fragment in BLOCKED_PATH_FRAGMENTS)


def looks_like_program_url(url: str) -> bool:
    if is_blocked_url(url):
        return False
    parts = [part for part in urlparse(url).path.lower().split("/") if part]
    return any(
        part in _PROGRAM_PARTS
        or part.endswith("-affiliate-program")
        or part.endswith("-partner-program")
        for part in parts
    )


def is_usable(facts: ProgramFacts, url: str) -> bool:
    if facts.confidence < 0.3:
        return False
    if facts.commission_type not in ALLOWED_TYPES:
        return False
    if facts.commission_type == "unknown" and facts.commission_value is None:
        return False
    if facts.commission_value is not None:
        if facts.commission_type.startswith("percent"):
            if not 0 < facts.commission_value <= 100:
                return False
        elif not 0 < facts.commission_value <= 100_000:
            return False
    if facts.cookie_days is not None and not 0 < facts.cookie_days <= 730:
        return False
    if is_blocked_url(url):
        return False
    if not facts.program_name.strip():
        return False
    return True

from revenue_swarm.config import getenv

SEARCH_STUB = getenv("SEARCH_STUB", "1") == "1"
SEARCH_PROVIDER = getenv("SEARCH_PROVIDER", "tavily")  # tabily | brave
SEARCH_API_KEY = getenv("SEARCH_API_KEY", "")
SEARCH_MAX_RESULTS = int(getenv("SEARCH_MAX_RESULTS", "10"))

RESEARCH_SOURCE = getenv("RESEARCH_SOURCE", "web")  # web | catalog
RESEARCH_NICHE = getenv("RESEARCH_NICHE", "help desk software")

FETCH_TIMEOUT = float(getenv("FETCH_TIMEOUT", "20"))
FETCH_USER_AGENT = getenv(
    "FETCH_USER_AGENT", "RevenueSwarmBot/0.1 (+https://example.com/bot)"
)
RESPECT_ROBOTS = getenv("RESPECT_ROBOTS", "1") == "1"
FETCH_CACHE_TTL = int(getenv("FETCH_CACHE_TTL", "86400"))

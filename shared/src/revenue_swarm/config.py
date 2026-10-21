import os


def getenv(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        msg = f"Missing required environment variable: {name}"
        raise RuntimeError(msg)
    return value


DATABASE_URL = getenv(
    "DATABASE_URL",
    "postgresql+psycopg://aiswarm:test1234@localhost:5432/swarm_db",
)
REDIS_URL = getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_STUB = getenv("LLM_STUB", "1") == "1"
OLLAMA_BASE_URL = getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = getenv("OLLAMA_MODEL", "llama3.2:1b")
LLM_PROVIDER = getenv("LLM_PROVIDER", "ollama")  # ollama | anthropic
LLM_QUALITY_MODEL = getenv("LLM_QUALITY_MODEL", "claude-sonnet-4.5")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "") or ""

# Storage configuration (MinIO / S3)
STORAGE_ENDPOINT = getenv("STORAGE_ENDPOINT", "http://minio:9000")
STORAGE_PUBLIC_ENDPOINT = getenv(
    "STORAGE_PUBLIC_ENDPOINT", "http://localhost:9000"
)
STORAGE_BUCKET = getenv("STORAGE_BUCKET", "revenue-assets")
STORAGE_ACCESS_KEY = getenv("STORAGE_ACCESS_KEY", "minio")
STORAGE_SECRET_KEY = getenv("STORAGE_SECRET_KEY", "minio12345")
STORAGE_REGION = getenv("STORAGE_REGION", "us-east-1")

# Ebook pipeline
EBOOK_ENABLED = getenv("EBOOK_ENABLED", "1") == "1"
EBOOK_MAX_CHAPTERS = int(getenv("EBOOK_MAX_CHAPTERS", "12"))
EBOOK_MAX_TOKENS_PER_BOOK = int(getenv("EBOOK_MAX_TOKENS_PER_BOOK", "200000"))
EBOOK_MIN_HUMAN_REVIEW = getenv("EBOOK_MIN_HUMAN_REVIEW", "1") == "1"

# Sales & Monetization
SALES_ENABLED = getenv("SALES_ENABLED", "0") == "1"
PAYMENT_PROVIDER = getenv("PAYMENT_PROVIDER", "fake")
PAYMENT_MODE = getenv("PAYMENT_MODE", "test")
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "") or ""
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "") or ""
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "") or ""
LS_STORE_ID = os.getenv("LS_STORE_ID", "") or ""
FAKE_WEBHOOK_SECRET = getenv("FAKE_WEBHOOK_SECRET", "dev-only")

# Email & Delivery
EMAIL_PROVIDER = getenv("EMAIL_PROVIDER", "console")
EMAIL_FROM = (
    os.getenv("EMAIL_FROM", "noreply@example.com") or "noreply@example.com"
)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "") or ""
PUBLIC_BASE_URL = getenv("PUBLIC_BASE_URL", "http://localhost:3000")
SUCCESS_URL = getenv("SUCCESS_URL", "http://localhost:3000/p/success")
CANCEL_URL = getenv("CANCEL_URL", "http://localhost:3000/p/cancel")
DOWNLOAD_TOKEN_TTL_DAYS = int(getenv("DOWNLOAD_TOKEN_TTL_DAYS", "30"))
DOWNLOAD_MAX_PER_GRANT = int(getenv("DOWNLOAD_MAX_PER_GRANT", "5"))

# Affiliate operations
AFFILIATE_LINKS_ENABLED = getenv("AFFILIATE_LINKS_ENABLED", "0") == "1"
AFFILIATE_NETWORKS = getenv("AFFILIATE_NETWORKS", "manual")
LINK_REDIRECT_ENABLED = getenv("LINK_REDIRECT_ENABLED", "1") == "1"
LINK_CHECK_ENABLED = getenv("LINK_CHECK_ENABLED", "1") == "1"
LINK_CHECK_BATCH = int(getenv("LINK_CHECK_BATCH", "50"))
NETWORK_RATE_LIMIT = int(getenv("NETWORK_RATE_LIMIT", "30"))

MIN_CLICKS_FOR_EPC = int(getenv("MIN_CLICKS_FOR_EPC", "100"))
EPC_WINDOW_DAYS = int(getenv("EPC_WINDOW_DAYS", "90"))
EPC_PRIOR_WEIGHT = int(getenv("EPC_PRIOR_WEIGHT", "100"))
SYNC_DAYS_BACK = int(getenv("SYNC_DAYS_BACK", "7"))
TOKEN_CENTS = int(getenv("TOKEN_CENTS", "0"))

# Public base for /go/{slug}; Next.js rewrites /go/* to the backend.
SITE_URL = getenv("SITE_URL", PUBLIC_BASE_URL).rstrip("/")
LINK_FALLBACK_URL = getenv("LINK_FALLBACK_URL", SITE_URL)

AWIN_PUBLISHER_ID = os.getenv("AWIN_PUBLISHER_ID", "") or ""
AWIN_API_TOKEN = os.getenv("AWIN_API_TOKEN", "") or ""
IMPACT_ACCOUNT_SID = os.getenv("IMPACT_ACCOUNT_SID", "") or ""
IMPACT_AUTH_TOKEN = os.getenv("IMPACT_AUTH_TOKEN", "") or ""
CJ_API_KEY = os.getenv("CJ_API_KEY", "") or ""
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "") or ""

NETWORK_SECRETS = tuple(
    s for s in (AWIN_API_TOKEN, IMPACT_AUTH_TOKEN, CJ_API_KEY) if s
)

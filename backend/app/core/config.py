import os


def getenv(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        msg = f"Missing required environmentvariable: {name}"
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

HITL_ACTOR = getenv("HITL_ACTOR", "operator")

CORS_ORIGINS = getenv("CORS_ORIGINS", "http://localhost:3000")
DASHBOARD_URL = getenv("DASHBOARD_URL", "http://localhost:3000")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "") or ""
WEBHOOK_KIND = os.getenv("WEBHOOK_KIND", "discord")  # slack | discord

import os

from revenue_swarm.config import getenv

HITL_ACTOR = getenv("HITL_ACTOR", "operator")

CORS_ORIGINS = getenv("CORS_ORIGINS", "http://localhost:3000")
DASHBOARD_URL = getenv("DASHBOARD_URL", "http://localhost:3000")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "") or ""
WEBHOOK_KIND = os.getenv("WEBHOOK_KIND", "discord")  # slack | discord

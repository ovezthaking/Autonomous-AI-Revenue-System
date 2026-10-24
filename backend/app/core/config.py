import os

from revenue_swarm.config import getenv

HITL_ACTOR = getenv("HITL_ACTOR", "operator")

CORS_ORIGINS = getenv("CORS_ORIGINS", "http://localhost:3000")
DASHBOARD_URL = getenv("DASHBOARD_URL", "http://localhost:3000")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "") or ""
WEBHOOK_KIND = os.getenv("WEBHOOK_KIND", "discord")  # slack | discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "") or ""
DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY", "") or ""
DISCORD_APPLICATION_ID = os.getenv("DISCORD_APPLICATION_ID", "") or ""
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "") or ""
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "") or ""
DISCORD_ALLOWED_USER_IDS = frozenset(
    part.strip()
    for part in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",")
    if part.strip()
)
DISCORD_CARDS_ENABLED = bool(DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID)

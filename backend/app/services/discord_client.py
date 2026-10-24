import logging

import httpx

from app.core.config import (
    DISCORD_APPLICATION_ID,
    DISCORD_BOT_TOKEN,
    DISCORD_CARDS_ENABLED,
    DISCORD_CHANNEL_ID,
    DISCORD_GUILD_ID,
)

logger = logging.getLogger(__name__)
_API = "https://discord.com/api/v10"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "User-Agent": "RevenueSwarm/0.1",
        "Content-Type": "application/json",
    }


def post_channel_message(payload: dict) -> str | None:
    if not DISCORD_CARDS_ENABLED:
        return None
    url = f"{_API}/channels/{DISCORD_CHANNEL_ID}/messages"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=_headers(), json=payload)
            response.raise_for_status()
            return str(response.json()["id"])
    except Exception:
        logger.exception("Discord card post failed")
        return None


def edit_channel_message(message_id: str, payload: dict) -> None:
    if not DISCORD_CARDS_ENABLED:
        return
    url = f"{_API}/channels/{DISCORD_CHANNEL_ID}/messages/{message_id}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.patch(url, headers=_headers(), json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("Discord card edit failed")


def register_guild_commands(commands: list[dict]) -> None:
    if not (DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID and DISCORD_GUILD_ID):
        msg = "Discord command registration is not configured"
        raise RuntimeError(msg)
    url = (
        f"{_API}/applications/{DISCORD_APPLICATION_ID}"
        f"/guilds/{DISCORD_GUILD_ID}/commands"
    )
    with httpx.Client(timeout=10.0) as client:
        response = client.put(url, headers=_headers(), json=commands)
        response.raise_for_status()

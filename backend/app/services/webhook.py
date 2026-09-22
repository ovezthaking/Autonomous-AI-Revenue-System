import logging

import httpx

from app.core.config import DASHBOARD_URL, WEBHOOK_KIND, WEBHOOK_URL

logger = logging.getLogger(__name__)


def notify_hitl_decision(label: str, entity_status: str) -> None:
    if not WEBHOOK_URL:
        return
    text = f"HITL: *{label}* -> `{entity_status}`\n{DASHBOARD_URL}"
    if WEBHOOK_KIND == "discord":
        payload = {"content": text.replace("*", "**")}
    else:
        payload = {"text": text}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(WEBHOOK_URL, json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("HITL webhook failed")

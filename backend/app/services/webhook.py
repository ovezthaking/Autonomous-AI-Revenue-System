import logging

import httpx

from app.core.config import DASHBOARD_URL, WEBHOOK_KIND, WEBHOOK_URL
from app.models.affiliate_program import AffiliateProgram

logger = logging.getLogger(__name__)


def notify_hitl_decision(row: AffiliateProgram) -> None:
    if not WEBHOOK_URL:
        return
    text = f"HITL: *{row.name}* -> `{row.status}`\n{DASHBOARD_URL}"
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

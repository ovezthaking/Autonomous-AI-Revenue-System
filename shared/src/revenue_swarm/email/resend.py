import logging

import httpx

from revenue_swarm import config
from revenue_swarm.email.console import ConsoleEmail
from revenue_swarm.models.order import Order

log = logging.getLogger(__name__)


class ResendEmail:
    def send(self, to: str, subject: str, body: str) -> None:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
            json={
                "from": config.EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "text": body,
            },
            timeout=20,
        )
        response.raise_for_status()


def send_delivery_email(order: Order, token: str) -> None:
    sender = (
        ResendEmail() if config.EMAIL_PROVIDER == "resend" else ConsoleEmail()
    )
    link = f"{config.PUBLIC_BASE_URL}/download/{token}"
    sender.send(order.email or "", "Your download", link)
    log.info("delivery token=%s", token[:8])

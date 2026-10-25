import logging

from revenue_swarm.models.hitl_discord_message import HitlDiscordMessage
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import (
    DASHBOARD_URL,
    DISCORD_CARDS_ENABLED,
    DISCORD_CHANNEL_ID,
)
from app.services.discord_cards import decided_payload, pending_payload
from app.services.discord_client import (
    edit_channel_message,
    post_channel_message,
)
from app.services.hitl_subject import HitlSubject

logger = logging.getLogger(__name__)


def notify_proposed(db: Session, subject: HitlSubject) -> None:
    if not DISCORD_CARDS_ENABLED:
        return
    try:
        message_id = post_channel_message(
            pending_payload(subject, DASHBOARD_URL)
        )
        if message_id is None:
            return
        db.add(
            HitlDiscordMessage(
                entity_type=subject.entity_type,
                entity_id=subject.entity_id,
                channel_id=DISCORD_CHANNEL_ID,
                message_id=message_id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.exception("Discord card already stored")
    except Exception:
        db.rollback()
        logger.exception("Discord card notify failed")


def edit_decided_card(db: Session, subject: HitlSubject, actor: str) -> None:
    if not DISCORD_CARDS_ENABLED:
        return
    try:
        row = db.scalar(
            select(HitlDiscordMessage).where(
                HitlDiscordMessage.entity_type == subject.entity_type,
                HitlDiscordMessage.entity_id == subject.entity_id,
            )
        )
        if row is None:
            return
        edit_channel_message(
            row.message_id,
            decided_payload(subject, DASHBOARD_URL, actor),
        )
    except Exception:
        logger.exception("Discord card sync failed")

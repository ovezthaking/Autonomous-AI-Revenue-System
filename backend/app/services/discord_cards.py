import re
import uuid

from app.services.hitl_subject import HitlSubject

_CUSTOM_ID = re.compile(
    r"(?P<entity_type>[a-z_]+):"
    r"(?P<entity_id>[0-9a-fA-F-]{36}):"
    r"(?P<action>approve|reject)"
)


def parse_custom_id(
    custom_id: str,
) -> tuple[str, uuid.UUID, str] | None:
    match = _CUSTOM_ID.fullmatch(custom_id)
    if match is None:
        return None
    try:
        entity_id = uuid.UUID(match.group("entity_id"))
    except ValueError:
        return None
    return (
        match.group("entity_type"),
        entity_id,
        match.group("action"),
    )


def _clip(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _lines(subject: HitlSubject, dashboard_url: str) -> str:
    parts = [_clip(subject.detail), subject.url or "", dashboard_url]
    extra = "\n".join(part for part in parts if part)
    return extra


def pending_payload(subject: HitlSubject, dashboard_url: str) -> dict:
    content = f"**{subject.label}** is waiting for a decision."
    extra = _lines(subject, dashboard_url)
    if extra:
        content = f"{content}\n{extra}"
    custom_base = f"{subject.entity_type}:{subject.entity_id}"
    return {
        "content": content[:2000],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 3,
                        "label": "Approve",
                        "custom_id": f"{custom_base}:approve",
                    },
                    {
                        "type": 2,
                        "style": 4,
                        "label": "Reject",
                        "custom_id": f"{custom_base}:reject",
                    },
                ],
            }
        ],
    }


def decided_payload(
    subject: HitlSubject, dashboard_url: str, actor: str
) -> dict:
    content = f"**{subject.label}** is `{subject.status}` by `{actor}`."
    extra = _lines(subject, dashboard_url)
    if extra:
        content = f"{content}\n{extra}"
    return {"content": content[:2000], "components": []}

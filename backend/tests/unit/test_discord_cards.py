import uuid

from app.services.discord_cards import (
    decided_payload,
    parse_custom_id,
    pending_payload,
)
from app.services.hitl_subject import HitlSubject


def _subject() -> HitlSubject:
    return HitlSubject(
        entity_type="affiliate_program",
        entity_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        label="ACME",
        detail="Worth it.",
        url="https://example.com",
        status="proposed",
    )


def test_pending_payload_has_two_buttons():
    payload = pending_payload(_subject(), "http://localhost:3000")
    buttons = payload["components"][0]["components"]
    assert [b["label"] for b in buttons] == ["Approve", "Reject"]
    assert buttons[0]["custom_id"].endswith(":approve")
    assert buttons[1]["custom_id"].endswith(":reject")


def test_decided_payload_has_no_buttons():
    subject = _subject()
    decided = HitlSubject(
        entity_type=subject.entity_type,
        entity_id=subject.entity_id,
        label=subject.label,
        detail=subject.detail,
        url=subject.url,
        status="approved",
    )
    payload = decided_payload(decided, "http://localhost:3000", "discord:9")
    assert payload["components"] == []
    assert "approved" in payload["content"]
    assert "discord:9" in payload["content"]


def test_parse_custom_id_roundtrip():
    subject = _subject()
    custom_id = pending_payload(subject, "http://localhost:3000")[
        "components"
    ][0]["components"][0]["custom_id"]
    parsed = parse_custom_id(custom_id)
    assert parsed == (subject.entity_type, subject.entity_id, "approve")


def test_parse_custom_id_rejects_garbage():
    assert parse_custom_id("nope") is None
    assert parse_custom_id(f"affiliate_program:{'-' * 36}:approve") is None

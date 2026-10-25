import uuid
from unittest.mock import MagicMock

from app.services import discord_interactions
from app.services.discord_interactions import handle_interaction
from fastapi import HTTPException
from revenue_swarm.enums import HitlDecisionValue, ProgramStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram

ALLOWED = frozenset({"42"})
DASHBOARD = "http://localhost:3000"


def _program(
    name: str = "ACME", status: str = ProgramStatus.PROPOSED.value
) -> AffiliateProgram:
    row = AffiliateProgram(name=name, status=status)
    row.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    return row


def _button_payload(custom_id: str, user_id: str = "42") -> dict:
    return {
        "type": 3,
        "member": {"user": {"id": user_id}},
        "data": {"custom_id": custom_id},
    }


def _command_payload(
    name: str, program_value: str, user_id: str = "42"
) -> dict:
    return {
        "type": 2,
        "member": {"user": {"id": user_id}},
        "data": {
            "name": name,
            "options": [{"name": "program", "value": program_value}],
        },
    }


def test_ping_returns_pong_without_calling_decide_program(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    res = handle_interaction(
        db, {"type": 1}, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res == {"type": 1}
    assert called == []


def test_unauthorized_user_button_returns_ephemeral(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    program = _program()
    payload = _button_payload(
        f"affiliate_program:{program.id}:approve", user_id="999"
    )
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res == {
        "type": 4,
        "data": {"content": "You cannot decide.", "flags": 64},
    }
    assert called == []


def test_button_with_foreign_entity_type_returns_ephemeral(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    uid = uuid.uuid4()
    payload = _button_payload(f"content_item:{uid}:approve")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res["type"] == 4
    assert res["data"]["flags"] == 64
    assert called == []


def test_approve_button_on_proposed_calls_decide_and_returns_type_7(
    monkeypatch,
):
    db = MagicMock()
    program = _program()
    db.get.return_value = program
    calls = []

    def fake_decide(session, pid, decision, comment, actor=None):
        calls.append((session, pid, decision, comment, actor))
        approved = _program(status=ProgramStatus.APPROVED.value)
        approved.id = pid
        return approved

    monkeypatch.setattr(discord_interactions, "decide_program", fake_decide)
    payload = _button_payload(f"affiliate_program:{program.id}:approve")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert calls == [
        (db, program.id, HitlDecisionValue.APPROVED, None, "discord:42")
    ]
    assert res["type"] == 7
    assert res["data"]["components"] == []
    assert "approved" in res["data"]["content"]
    assert "discord:42" in res["data"]["content"]


def test_409_conflict_returns_ephemeral_starting_with_program_already(
    monkeypatch,
):
    db = MagicMock()
    program = _program(status=ProgramStatus.APPROVED.value)
    db.get.return_value = program
    db.scalar.return_value = "operator"

    def fake_decide(*_a, **_kw):
        raise HTTPException(status_code=409, detail="Program already approved")

    monkeypatch.setattr(discord_interactions, "decide_program", fake_decide)
    payload = _button_payload(f"affiliate_program:{program.id}:approve")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res["type"] == 4
    assert res["data"]["flags"] == 64
    assert res["data"]["content"].startswith("Program already")


def test_approve_command_by_case_insensitive_name(monkeypatch):
    db = MagicMock()
    program = _program(name="ACME")
    scalars_result = MagicMock()
    scalars_result.all.return_value = [program]
    db.scalars.return_value = scalars_result

    def fake_decide(session, pid, decision, comment, actor=None):
        approved = _program(name="ACME", status=ProgramStatus.APPROVED.value)
        approved.id = pid
        return approved

    monkeypatch.setattr(discord_interactions, "decide_program", fake_decide)
    payload = _command_payload("approve", "acme")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res == {
        "type": 4,
        "data": {"content": "Approved ACME.", "flags": 64},
    }


def test_command_with_duplicate_proposed_names_refuses(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [_program("ACME"), _program("ACME")]
    db.scalars.return_value = scalars_result

    payload = _command_payload("approve", "ACME")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res["type"] == 4
    assert res["data"]["flags"] == 64
    assert "Use the id" in res["data"]["content"]
    assert called == []


def test_command_with_unknown_name_returns_ephemeral(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    db.scalars.return_value = scalars_result

    payload = _command_payload("approve", "NONEXISTENT")
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res["type"] == 4
    assert res["data"]["flags"] == 64
    assert called == []


def test_command_with_missing_uuid_returns_program_not_found(monkeypatch):
    called = []
    monkeypatch.setattr(
        discord_interactions,
        "decide_program",
        lambda *a, **kw: called.append((a, kw)),
    )
    db = MagicMock()
    db.get.return_value = None

    payload = _command_payload("approve", str(uuid.uuid4()))
    res = handle_interaction(
        db, payload, allowed=ALLOWED, dashboard_url=DASHBOARD
    )
    assert res == {
        "type": 4,
        "data": {"content": "Program not found.", "flags": 64},
    }
    assert called == []

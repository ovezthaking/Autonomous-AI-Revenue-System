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


def test_command_option_missing_and_empty_program_and_uuid_resolution(
    monkeypatch,
):
    import pytest

    db = MagicMock()
    # 1. Unknown command name -> line 214
    res_unknown_cmd = handle_interaction(
        db,
        _command_payload("archive", "acme"),
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_unknown_cmd["data"]["content"] == "Unknown command."

    # 2. Missing option -> command_option returns "" -> "Missing program."
    res_missing_opt = handle_interaction(
        db,
        {
            "type": 2,
            "member": {"user": {"id": "42"}},
            "data": {"name": "approve", "options": [{"name": "other"}]},
        },
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_missing_opt["data"]["content"] == "Missing program."

    # 3. Valid UUID resolution (line 61) + _apply error in command (line 220)
    program = _program(name="ACME", status=ProgramStatus.APPROVED.value)
    db.get.side_effect = [program, None]

    def fake_decide_409(*_a, **_kw):
        raise HTTPException(status_code=409, detail="conflict")

    monkeypatch.setattr(
        discord_interactions, "decide_program", fake_decide_409
    )
    res_cmd_err = handle_interaction(
        db,
        _command_payload("approve", str(program.id)),
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_cmd_err["data"]["content"] == "Program already decided."

    # 4. Non-409 HTTPException in _apply re-raises (line 124)
    db.get.side_effect = None
    db.get.return_value = program

    def fake_decide_500(*_a, **_kw):
        raise HTTPException(status_code=500, detail="boom")

    monkeypatch.setattr(
        discord_interactions, "decide_program", fake_decide_500
    )
    with pytest.raises(HTTPException) as exc_info:
        handle_interaction(
            db,
            _command_payload("reject", str(program.id)),
            allowed=ALLOWED,
            dashboard_url=DASHBOARD,
        )
    assert exc_info.value.status_code == 500


def test_unsupported_interaction_and_button_edge_cases(monkeypatch):
    import pytest
    from revenue_swarm.models.product_listing import ProductListing

    db = MagicMock()

    # 1. Unsupported interaction type (line 91)
    res_unsup = handle_interaction(
        db,
        {"type": 99, "member": {"user": {"id": "42"}}},
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_unsup["data"]["content"] == "Unsupported interaction."

    # 2. Unknown button custom_id (line 163)
    res_bad_btn = handle_interaction(
        db,
        _button_payload("invalid-custom-id"),
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_bad_btn["data"]["content"] == "Unknown button."

    # 3. Affiliate program button when program not in DB (line 168)
    uid = uuid.uuid4()
    db.get.return_value = None
    res_missing_prog = handle_interaction(
        db,
        _button_payload(f"affiliate_program:{uid}:approve"),
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_missing_prog["data"]["content"] == "Program not found."

    # 4. Product idea button: 404, 409, and 500 re-raise (lines 182-187)
    for code, expected in [
        (404, "Idea not found."),
        (409, "Idea already decided."),
    ]:
        monkeypatch.setattr(
            discord_interactions,
            "decide_product_idea",
            MagicMock(side_effect=HTTPException(status_code=code)),
        )
        res = handle_interaction(
            db,
            _button_payload(f"product_idea:{uid}:approve"),
            allowed=ALLOWED,
            dashboard_url=DASHBOARD,
        )
        assert res["data"]["content"] == expected

    monkeypatch.setattr(
        discord_interactions,
        "decide_product_idea",
        MagicMock(side_effect=HTTPException(status_code=500)),
    )
    with pytest.raises(HTTPException):
        handle_interaction(
            db,
            _button_payload(f"product_idea:{uid}:approve"),
            allowed=ALLOWED,
            dashboard_url=DASHBOARD,
        )

    # 5. Shop listing button: success, 404, 409, and 500 re-raise
    fake_listing = ProductListing(
        id=uid,
        product_id=uuid.uuid4(),
        platform="shopify",
        handle="rs-item",
        status="active",
    )
    monkeypatch.setattr(
        discord_interactions,
        "decide_listing",
        lambda *_a, **_kw: fake_listing,
    )
    res_listing_ok = handle_interaction(
        db,
        _button_payload(f"shop_listing:{uid}:approve"),
        allowed=ALLOWED,
        dashboard_url=DASHBOARD,
    )
    assert res_listing_ok["type"] == 7
    assert "rs-item" in res_listing_ok["data"]["content"]

    for code, expected in [
        (404, "Listing not found."),
        (409, "Listing already decided."),
    ]:
        monkeypatch.setattr(
            discord_interactions,
            "decide_listing",
            MagicMock(side_effect=HTTPException(status_code=code)),
        )
        res = handle_interaction(
            db,
            _button_payload(f"shop_listing:{uid}:reject"),
            allowed=ALLOWED,
            dashboard_url=DASHBOARD,
        )
        assert res["data"]["content"] == expected

    monkeypatch.setattr(
        discord_interactions,
        "decide_listing",
        MagicMock(side_effect=HTTPException(status_code=500)),
    )
    with pytest.raises(HTTPException):
        handle_interaction(
            db,
            _button_payload(f"shop_listing:{uid}:reject"),
            allowed=ALLOWED,
            dashboard_url=DASHBOARD,
        )

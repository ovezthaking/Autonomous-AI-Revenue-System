"""Unit tests for discord_client, discord_hitl, webhook, discord_cards worker,
and discord_register CLI."""

import runpy
import uuid
from unittest.mock import MagicMock

import pytest
from app import discord_register
from app.services import discord_client, discord_hitl, webhook
from app.services.hitl_subject import HitlSubject
from app.workers import discord_cards as discord_cards_worker
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.hitl_discord_message import HitlDiscordMessage
from sqlalchemy.exc import IntegrityError


def _subject() -> HitlSubject:
    return HitlSubject(
        entity_type="affiliate_program",
        entity_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        label="ACME",
        detail="Great program",
        url="https://acme.example",
        status="proposed",
    )


def test_discord_client_post_edit_and_register(monkeypatch):
    # 1. Disabled cards -> noop / None
    monkeypatch.setattr(discord_client, "DISCORD_CARDS_ENABLED", False)
    assert discord_client.post_channel_message({"content": "hi"}) is None
    assert discord_client.edit_channel_message("m1", {"content": "hi"}) is None

    # 2. Enabled cards -> success & failure branches
    monkeypatch.setattr(discord_client, "DISCORD_CARDS_ENABLED", True)
    monkeypatch.setattr(discord_client, "DISCORD_CHANNEL_ID", "chan_1")
    monkeypatch.setattr(discord_client, "DISCORD_BOT_TOKEN", "tok_1")

    fake_resp = MagicMock()
    fake_resp.json.return_value = {"id": "msg_99"}
    fake_http = MagicMock()
    fake_http.__enter__.return_value = fake_http
    fake_http.post.return_value = fake_resp
    fake_http.patch.return_value = fake_resp
    fake_http.put.return_value = fake_resp

    monkeypatch.setattr(
        discord_client.httpx, "Client", lambda **_kw: fake_http
    )

    msg_id = discord_client.post_channel_message({"content": "hello"})
    assert msg_id == "msg_99"
    discord_client.edit_channel_message("msg_99", {"content": "updated"})
    fake_http.patch.assert_called_once()

    # Exception branches in post and edit
    fake_http.post.side_effect = RuntimeError("network down")
    assert discord_client.post_channel_message({"content": "hello"}) is None

    fake_http.patch.side_effect = RuntimeError("network down")
    discord_client.edit_channel_message("msg_99", {"content": "updated"})

    # 3. register_guild_commands: unconfigured raises RuntimeError
    monkeypatch.setattr(discord_client, "DISCORD_APPLICATION_ID", "")
    with pytest.raises(RuntimeError, match="not configured"):
        discord_client.register_guild_commands([])

    # Configured -> PUT succeeds
    monkeypatch.setattr(discord_client, "DISCORD_APPLICATION_ID", "app_1")
    monkeypatch.setattr(discord_client, "DISCORD_GUILD_ID", "guild_1")
    discord_client.register_guild_commands([{"name": "approve"}])
    fake_http.put.assert_called_once()


def test_discord_hitl_notify_proposed_and_edit_decided_card(monkeypatch):
    subj = _subject()
    db = MagicMock()

    # Disabled -> early return
    monkeypatch.setattr(discord_hitl, "DISCORD_CARDS_ENABLED", False)
    discord_hitl.notify_proposed(db, subj)
    discord_hitl.edit_decided_card(db, subj, "operator")
    db.add.assert_not_called()

    # Enabled
    monkeypatch.setattr(discord_hitl, "DISCORD_CARDS_ENABLED", True)
    monkeypatch.setattr(discord_hitl, "DISCORD_CHANNEL_ID", "chan_1")

    # 1. post_channel_message returns None
    monkeypatch.setattr(discord_hitl, "post_channel_message", lambda _p: None)
    discord_hitl.notify_proposed(db, subj)
    db.add.assert_not_called()

    # 2. post_channel_message returns message_id -> stores and commits
    monkeypatch.setattr(
        discord_hitl, "post_channel_message", lambda _p: "msg_123"
    )
    discord_hitl.notify_proposed(db, subj)
    db.add.assert_called_once()
    db.commit.assert_called_once()

    # 3. IntegrityError -> rollback
    db.reset_mock()
    db.commit.side_effect = IntegrityError("dup", {}, Exception())
    discord_hitl.notify_proposed(db, subj)
    db.rollback.assert_called_once()

    # 4. Generic Exception -> rollback
    db.reset_mock()
    db.commit.side_effect = RuntimeError("db error")
    discord_hitl.notify_proposed(db, subj)
    db.rollback.assert_called_once()

    # 5. edit_decided_card: row is None
    db.reset_mock()
    db.scalar.return_value = None
    edited = []
    monkeypatch.setattr(
        discord_hitl,
        "edit_channel_message",
        lambda mid, payload: edited.append((mid, payload)),
    )
    discord_hitl.edit_decided_card(db, subj, "operator")
    assert edited == []

    # 6. edit_decided_card: row exists -> calls edit_channel_message
    db.scalar.return_value = HitlDiscordMessage(
        entity_type=subj.entity_type,
        entity_id=subj.entity_id,
        channel_id="chan_1",
        message_id="msg_123",
    )
    discord_hitl.edit_decided_card(db, subj, "operator")
    assert len(edited) == 1
    assert edited[0][0] == "msg_123"

    # 7. edit_decided_card: exception caught and logged
    db.scalar.side_effect = RuntimeError("boom")
    discord_hitl.edit_decided_card(db, subj, "operator")


def test_webhook_notify_hitl_decision(monkeypatch):
    # 1. No WEBHOOK_URL -> noop
    monkeypatch.setattr(webhook, "WEBHOOK_URL", "")
    webhook.notify_hitl_decision("ACME", "approved")

    # 2. Discord webhook kind vs generic slack/text kind
    sent_payloads = []
    fake_resp = MagicMock()
    fake_http = MagicMock()
    fake_http.__enter__.return_value = fake_http

    def _post(url, json):
        sent_payloads.append((url, json))
        return fake_resp

    fake_http.post.side_effect = _post
    monkeypatch.setattr(webhook.httpx, "Client", lambda **_kw: fake_http)
    monkeypatch.setattr(webhook, "WEBHOOK_URL", "https://hooks.test/1")

    monkeypatch.setattr(webhook, "WEBHOOK_KIND", "discord")
    webhook.notify_hitl_decision("ACME", "approved")
    assert "**ACME**" in sent_payloads[-1][1]["content"]

    monkeypatch.setattr(webhook, "WEBHOOK_KIND", "slack")
    webhook.notify_hitl_decision("ACME", "rejected")
    assert "*ACME*" in sent_payloads[-1][1]["text"]

    # 3. Exception during post is caught
    fake_http.post.side_effect = RuntimeError("webhook error")
    webhook.notify_hitl_decision("ACME", "approved")


def test_discord_cards_worker_task(monkeypatch):
    fake_db = MagicMock()
    monkeypatch.setattr(discord_cards_worker, "SessionLocal", lambda: fake_db)
    notified = []
    monkeypatch.setattr(
        discord_cards_worker,
        "notify_proposed",
        lambda db, subj: notified.append((db, subj)),
    )

    # 1. Missing program -> closes db without calling notify_proposed
    fake_db.get.return_value = None
    uid = uuid.uuid4()
    discord_cards_worker.notify_proposed_task.run(str(uid))
    assert notified == []
    fake_db.close.assert_called_once()

    # 2. Existing program -> calls notify_proposed and closes db
    fake_db.reset_mock()
    prog = AffiliateProgram(
        id=uid, name="ACME", status="proposed", url="https://acme.test"
    )
    fake_db.get.return_value = prog
    discord_cards_worker.notify_proposed_task.run(str(uid))
    assert len(notified) == 1
    assert notified[0][1].entity_id == uid
    fake_db.close.assert_called_once()


def test_discord_register_cli(monkeypatch):
    import sys

    registered = []
    monkeypatch.setattr(
        discord_register,
        "register_guild_commands",
        lambda cmds: registered.append(cmds),
    )
    discord_register.main()
    assert registered == [discord_register.COMMANDS]

    monkeypatch.setattr(
        discord_client,
        "register_guild_commands",
        lambda cmds: registered.append(cmds),
    )
    sys.modules.pop("app.discord_register", None)
    runpy.run_module("app.discord_register", run_name="__main__")
    assert len(registered) == 2

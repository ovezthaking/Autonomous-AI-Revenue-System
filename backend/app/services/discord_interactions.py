import uuid

from fastapi import HTTPException
from revenue_swarm.enums import (
    HitlDecisionValue,
    HitlEntityType,
    ProgramStatus,
)
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.hitl_decision import HitlDecision
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.discord_auth import is_allowed
from app.services.discord_cards import decided_payload, parse_custom_id
from app.services.discord_hitl import edit_decided_card
from app.services.hitl import decide_program
from app.services.hitl_subject import subject_from_program


def ephemeral(text: str) -> dict:
    return {"type": 4, "data": {"content": text, "flags": 64}}


def discord_user_id(payload: dict) -> str:
    member = payload.get("member") or {}
    user = member.get("user") or payload.get("user") or {}
    return str(user.get("id") or "")


def command_option(payload: dict, name: str) -> str:
    options = (payload.get("data") or {}).get("options") or []
    for option in options:
        if option.get("name") == name:
            return str(option.get("value") or "").strip()
    return ""


def resolve_program(
    db: Session, raw: str
) -> tuple[AffiliateProgram | None, str | None]:
    text = raw.strip()
    if not text:
        return None, "Missing program."
    try:
        program_id = uuid.UUID(text)
    except ValueError:
        program_id = None
    if program_id is not None:
        row = db.get(AffiliateProgram, program_id)
        if row is None:
            return None, "Program not found."
        return row, None
    stmt = select(AffiliateProgram).where(
        func.lower(AffiliateProgram.name) == text.lower(),
        AffiliateProgram.status == ProgramStatus.PROPOSED.value,
    )
    rows = list(db.scalars(stmt).all())
    if len(rows) == 0:
        return None, "No proposed program with that name."
    if len(rows) > 1:
        return None, "Several programs share that name. Use the id."
    return rows[0], None


def handle_interaction(
    db: Session,
    payload: dict,
    *,
    allowed: frozenset[str],
    dashboard_url: str,
) -> dict:
    kind = payload.get("type")
    if kind == 1:
        return {"type": 1}
    user_id = discord_user_id(payload)
    if not is_allowed(user_id, allowed):
        return ephemeral("You cannot decide.")
    if kind == 3:
        return _handle_button(db, payload, user_id, dashboard_url)
    if kind == 2:
        return _handle_command(db, payload, user_id)
    return ephemeral("Unsupported interaction.")


def _apply(
    db: Session,
    row: AffiliateProgram,
    action: str,
    user_id: str,
) -> tuple[AffiliateProgram | None, str | None]:
    decision = (
        HitlDecisionValue.APPROVED
        if action == "approve"
        else HitlDecisionValue.REJECTED
    )
    try:
        updated = decide_program(
            db,
            row.id,
            decision,
            None,
            actor=f"discord:{user_id}",
        )
    except HTTPException as exc:
        if exc.status_code == 409:
            current = db.get(AffiliateProgram, row.id)
            if current is not None:
                edit_decided_card(
                    db,
                    subject_from_program(current),
                    _decision_actor(db, current.id),
                )
                return None, f"Program already {current.status}."
            return None, "Program already decided."
        raise
    return updated, None


def _decision_actor(db: Session, entity_id: uuid.UUID) -> str:
    stmt = (
        select(HitlDecision.actor)
        .where(
            HitlDecision.entity_type == HitlEntityType.AFFILIATE_PROGRAM.value,
            HitlDecision.entity_id == entity_id,
        )
        .order_by(HitlDecision.created_at.desc())
        .limit(1)
    )
    actor = db.scalar(stmt)
    return actor if isinstance(actor, str) else "operator"


def _handle_button(
    db: Session,
    payload: dict,
    user_id: str,
    dashboard_url: str,
) -> dict:
    custom_id = str((payload.get("data") or {}).get("custom_id") or "")
    parsed = parse_custom_id(custom_id)
    if parsed is None:
        return ephemeral("Unknown button.")
    entity_type, entity_id, action = parsed
    if entity_type != HitlEntityType.AFFILIATE_PROGRAM.value:
        return ephemeral("This decision is not wired yet.")
    row = db.get(AffiliateProgram, entity_id)
    if row is None:
        return ephemeral("Program not found.")
    updated, error = _apply(db, row, action, user_id)
    if error is not None or updated is None:
        return ephemeral(error or "Decision failed.")
    subject = subject_from_program(updated)
    body = decided_payload(subject, dashboard_url, f"discord:{user_id}")
    return {"type": 7, "data": body}


def _handle_command(db: Session, payload: dict, user_id: str) -> dict:
    name = str((payload.get("data") or {}).get("name") or "")
    if name not in {"approve", "reject"}:
        return ephemeral("Unknown command.")
    row, error = resolve_program(db, command_option(payload, "program"))
    if error is not None or row is None:
        return ephemeral(error or "Program not found.")
    updated, apply_error = _apply(db, row, name, user_id)
    if apply_error is not None or updated is None:
        return ephemeral(apply_error or "Decision failed.")
    verb = "Approved" if name == "approve" else "Rejected"
    return ephemeral(f"{verb} {updated.name}.")

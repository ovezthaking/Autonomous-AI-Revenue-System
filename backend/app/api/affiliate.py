"""Affiliate application pipeline: approved -> pending -> active/declined.

Applying stays manual (CAPTCHA, tax forms, ToS); this only tracks state.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from revenue_swarm.db import get_db
from revenue_swarm.enums import ApplicationStatus, ProgramStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.networks import KNOWN_NETWORKS
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.affiliate_program import ActivateBody, RecommendationRead

router = APIRouter(prefix="/applications", tags=["applications"])
DbSession = Annotated[Session, Depends(get_db)]

DECLINE_COOLDOWN_DAYS = 180
NEEDS_PROGRAM_ID = ("awin", "impact", "cj")
OPEN_STATES = (
    ApplicationStatus.NOT_APPLIED.value,
    ApplicationStatus.PENDING.value,
)


def _approved(db: Session, program_id: uuid.UUID) -> AffiliateProgram:
    row = db.get(AffiliateProgram, program_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if row.status != ProgramStatus.APPROVED.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Program is not approved"
        )
    return row


def _require_state(row: AffiliateProgram, *allowed: ApplicationStatus):
    if row.application_status not in {s.value for s in allowed}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot transition from {row.application_status}",
        )


@router.get("", response_model=list[RecommendationRead])
def list_applications(
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[AffiliateProgram]:
    states = (status_filter,) if status_filter else OPEN_STATES
    stmt = (
        select(AffiliateProgram)
        .where(
            AffiliateProgram.status == ProgramStatus.APPROVED.value,
            AffiliateProgram.application_status.in_(states),
        )
        .order_by(
            AffiliateProgram.score.desc().nulls_last(),
            AffiliateProgram.updated_at.asc(),
        )
    )
    return list(db.scalars(stmt).all())


@router.post("/{program_id}/applied", response_model=RecommendationRead)
def mark_applied(program_id: uuid.UUID, db: DbSession) -> AffiliateProgram:
    row = _approved(db, program_id)
    _require_state(
        row, ApplicationStatus.NOT_APPLIED, ApplicationStatus.DECLINED
    )
    row.application_status = ApplicationStatus.PENDING.value
    row.applied_at = datetime.now(UTC)
    extras = dict(row.extras or {})
    extras.pop("needs_reminder", None)
    row.extras = extras
    db.commit()
    db.refresh(row)
    return row


@router.post("/{program_id}/active", response_model=RecommendationRead)
def mark_active(
    program_id: uuid.UUID, body: ActivateBody, db: DbSession
) -> AffiliateProgram:
    row = _approved(db, program_id)
    _require_state(
        row,
        ApplicationStatus.NOT_APPLIED,
        ApplicationStatus.PENDING,
        ApplicationStatus.ACTIVE,
    )
    network = body.network.strip().lower()
    if network not in KNOWN_NETWORKS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown network; use one of {', '.join(KNOWN_NETWORKS)}",
        )
    program_ref = (body.network_program_id or "").strip() or None
    if network in NEEDS_PROGRAM_ID and program_ref is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"network_program_id is required for {network}",
        )
    if network == "manual" and not row.affiliate_link:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Paste the affiliate link before activating a manual program",
        )
    row.network = network
    row.network_program_id = program_ref
    row.application_status = ApplicationStatus.ACTIVE.value
    row.activated_at = datetime.now(UTC)
    row.allow_redirect = network != "amazon"
    extras = dict(row.extras or {})
    extras.pop("needs_reminder", None)
    row.extras = extras
    db.commit()
    db.refresh(row)
    return row


@router.post("/{program_id}/declined", response_model=RecommendationRead)
def mark_declined(program_id: uuid.UUID, db: DbSession) -> AffiliateProgram:
    row = _approved(db, program_id)
    _require_state(
        row, ApplicationStatus.NOT_APPLIED, ApplicationStatus.PENDING
    )
    until = datetime.now(UTC) + timedelta(days=DECLINE_COOLDOWN_DAYS)
    row.application_status = ApplicationStatus.DECLINED.value
    extras = dict(row.extras or {})
    extras.pop("needs_reminder", None)
    extras["declined_until"] = until.strftime("%Y-%m-%dT%H:%M:%SZ")
    row.extras = extras
    db.commit()
    db.refresh(row)
    return row

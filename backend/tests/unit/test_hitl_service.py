"""
Tests for `decide_program` in isolation from a real database: the SQLAlchemy
session is mocked (MagicMock), and the AffiliateProgram object is a regular
Python object created in memory (it never reaches the database). Thanks to
this, these tests only check the business logic (state transitions,
error codes) and run without Postgres.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from app.core.enums import HitlDecisionValue, HitlEntityType, ProgramStatus
from app.models.affiliate_program import AffiliateProgram
from app.services.hitl import decide_program
from fastapi import HTTPException


def _program(status: str) -> AffiliateProgram:
    row = AffiliateProgram(name="ACME", status=status)
    row.id = uuid.uuid4()
    return row


def test_decide_program_approves_a_proposed_program():
    db = MagicMock()
    program = _program(ProgramStatus.PROPOSED.value)
    db.get.return_value = program

    result = decide_program(
        db, program.id, HitlDecisionValue.APPROVED, "looks good"
    )

    assert result is program
    assert program.status == ProgramStatus.APPROVED.value
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(program)

    # we check that the HITL decision was added with correct fields
    added_decision = db.add.call_args[0][0]
    assert added_decision.entity_type == HitlEntityType.AFFILIATE_PROGRAM.value
    assert added_decision.entity_id == program.id
    assert added_decision.decision == HitlDecisionValue.APPROVED.value
    assert added_decision.comment == "looks good"


def test_decide_program_rejects_a_proposed_program():
    db = MagicMock()
    program = _program(ProgramStatus.PROPOSED.value)
    db.get.return_value = program

    result = decide_program(db, program.id, HitlDecisionValue.REJECTED, None)

    assert result.status == ProgramStatus.REJECTED.value
    added_decision = db.add.call_args[0][0]
    assert added_decision.decision == HitlDecisionValue.REJECTED.value
    assert added_decision.comment is None


@pytest.mark.parametrize(
    "current_status",
    [ProgramStatus.APPROVED.value, ProgramStatus.REJECTED.value],
)
def test_decide_program_rejects_double_decision(current_status):
    db = MagicMock()
    program = _program(current_status)
    db.get.return_value = program

    with pytest.raises(HTTPException) as exc_info:
        decide_program(db, program.id, HitlDecisionValue.APPROVED, None)

    assert exc_info.value.status_code == 409
    db.commit.assert_not_called()


def test_decide_program_raises_404_when_program_missing():
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        decide_program(db, uuid.uuid4(), HitlDecisionValue.APPROVED, None)

    assert exc_info.value.status_code == 404
    db.commit.assert_not_called()

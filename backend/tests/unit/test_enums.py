"""
Tests for enum values. They look trivial, but enums here
correspond to values kept as plain `Text` in database columns
(see app/models/*.py) — nothing in the database enforces compliance. If
someone accidentally changed an enum value, they would discreetly change
the API contract (e.g., the `status` value visible through JSON) without
any other signal. These tests are a cheap safety net for such a case.
"""

from app.core.enums import (
    ContentStatus,
    HitlDecisionValue,
    HitlEntityType,
    ProgramStatus,
)


def test_program_status_values():
    assert ProgramStatus.PROPOSED.value == "proposed"
    assert ProgramStatus.APPROVED.value == "approved"
    assert ProgramStatus.REJECTED.value == "rejected"


def test_content_status_values():
    assert ContentStatus.DRAFT.value == "draft"
    assert ContentStatus.APPROVED.value == "approved"
    assert ContentStatus.SCHEDULED.value == "scheduled"
    assert ContentStatus.PUBLISHED.value == "published"


def test_hitl_decision_value_values():
    assert HitlDecisionValue.APPROVED.value == "approved"
    assert HitlDecisionValue.REJECTED.value == "rejected"


def test_hitl_entity_type_values():
    assert HitlEntityType.AFFILIATE_PROGRAM.value == "affiliate_program"
    assert HitlEntityType.CONTENT_ITEM.value == "content_item"

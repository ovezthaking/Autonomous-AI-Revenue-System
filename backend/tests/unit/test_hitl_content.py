import uuid
from unittest.mock import MagicMock

import pytest
from app.services.hitl import decide_content
from fastapi import HTTPException
from revenue_swarm.enums import (
    ContentStatus,
    HitlDecisionValue,
    HitlEntityType,
)
from revenue_swarm.models.content_item import ContentItem


def _item(status: str) -> ContentItem:
    row = ContentItem(title="Review", body="Body", status=status)
    row.id = uuid.uuid4()
    return row


def test_decide_content_approves_a_draft():
    db = MagicMock()
    item = _item(ContentStatus.DRAFT.value)
    db.get.return_value = item

    result = decide_content(db, item.id, HitlDecisionValue.APPROVED, "ok")

    assert result is item
    assert item.status == ContentStatus.APPROVED.value
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(item)

    added_decision = db.add.call_args[0][0]
    assert added_decision.entity_type == HitlEntityType.CONTENT_ITEM.value
    assert added_decision.entity_id == item.id
    assert added_decision.decision == HitlDecisionValue.APPROVED.value
    assert added_decision.comment == "ok"


def test_decide_content_rejects_a_draft():
    db = MagicMock()
    item = _item(ContentStatus.DRAFT.value)
    db.get.return_value = item

    result = decide_content(db, item.id, HitlDecisionValue.REJECTED, None)

    assert result.status == ContentStatus.REJECTED.value
    added_decision = db.add.call_args[0][0]
    assert added_decision.entity_type == HitlEntityType.CONTENT_ITEM.value
    assert added_decision.decision == HitlDecisionValue.REJECTED.value
    assert added_decision.comment is None


@pytest.mark.parametrize(
    "current_status",
    [
        ContentStatus.APPROVED.value,
        ContentStatus.SCHEDULED.value,
        ContentStatus.PUBLISHED.value,
        ContentStatus.REJECTED.value,
    ],
)
def test_decide_content_rejects_non_draft(current_status):
    db = MagicMock()
    item = _item(current_status)
    db.get.return_value = item

    with pytest.raises(HTTPException) as exc_info:
        decide_content(db, item.id, HitlDecisionValue.APPROVED, None)

    assert exc_info.value.status_code == 409
    db.commit.assert_not_called()


def test_decide_content_raises_404_when_content_missing():
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        decide_content(db, uuid.uuid4(), HitlDecisionValue.APPROVED, None)

    assert exc_info.value.status_code == 404
    db.commit.assert_not_called()

import uuid
from datetime import UTC, datetime

import pytest
from app.schemas.affiliate_program import (
    HitlAction,
    RecommendationCreate,
    RecommendationRead,
)
from app.schemas.content_item import ContentItemRead
from app.schemas.task import TaskCreate
from pydantic import ValidationError


def test_recommendation_create_requires_name():
    with pytest.raises(ValidationError):
        RecommendationCreate()


def test_recommendation_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        RecommendationCreate(name="")


def test_recommendation_create_accepts_minimal_payload():
    payload = RecommendationCreate(name="ACME Affiliate")
    assert payload.name == "ACME Affiliate"
    assert payload.url is None
    assert payload.extras is None


def test_recommendation_create_accepts_full_payload():
    payload = RecommendationCreate(
        name="ACME Affiliate",
        url="https://acme.example/aff",
        network="ACME Network",
        category="SaaS",
        rationale="High EPC",
        extras={"epc": 4.2, "commission_pct": 30},
    )
    assert payload.extras == {"epc": 4.2, "commission_pct": 30}


def test_recommendation_read_exposes_affiliate_link():
    assert "affiliate_link" in RecommendationRead.model_fields


def test_content_item_read_accepts_operational_fields():
    now = datetime.now(UTC)
    item = ContentItemRead(
        id=uuid.uuid4(),
        affiliate_program_id=None,
        title="Review",
        body="Body",
        channel="blog",
        status="draft",
        source_task_id=None,
        extras={"generated_by": "content_agent_v1"},
        scheduled_for=None,
        published_at=None,
        updated_at=now,
        created_at=now,
    )
    assert item.source_task_id is None
    assert item.extras == {"generated_by": "content_agent_v1"}
    assert item.scheduled_for is None
    assert item.published_at is None
    assert item.updated_at == now


def test_hitl_action_comment_is_optional():
    assert HitlAction().comment is None
    assert HitlAction(comment="looks good").comment == "looks good"


def test_task_create_has_default_prompt():
    task = TaskCreate()
    assert "walking skeleton" in task.prompt.lower()


def test_task_create_rejects_empty_prompt():
    with pytest.raises(ValidationError):
        TaskCreate(prompt="")


def test_task_create_accepts_custom_prompt():
    task = TaskCreate(prompt="Write about Redis.")
    assert task.prompt == "Write about Redis."

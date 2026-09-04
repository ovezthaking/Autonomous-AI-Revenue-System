import pytest
from app.schemas.affiliate_program import HitlAction, RecommendationCreate
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

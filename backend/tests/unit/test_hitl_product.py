import uuid
from unittest.mock import MagicMock

import pytest
from app.services.hitl import decide_product
from fastapi import HTTPException
from revenue_swarm.enums import (
    HitlDecisionValue,
    HitlEntityType,
    ProductStatus,
)
from revenue_swarm.models.product import Product
from revenue_swarm.tasks import TaskName


def _product(status: str, extras: dict | None = None) -> Product:
    row = Product(
        slug="guide",
        title="Guide",
        price_cents=1900,
        status=status,
        extras=extras,
    )
    row.id = uuid.uuid4()
    return row


def _decide(product: Product, decision=HitlDecisionValue.APPROVED):
    db = MagicMock()
    db.get.return_value = product
    return db, decide_product(db, product.id, decision, "ok")


def test_approve_draft_moves_to_outlining_and_queues_outline(
    no_celery_broker,
):
    product = _product(ProductStatus.DRAFT.value)

    db, result = _decide(product)

    assert result.status == ProductStatus.OUTLINING.value
    assert no_celery_broker == [(TaskName.EBOOK_OUTLINE, [str(product.id)])]
    decision = db.add.call_args[0][0]
    assert decision.entity_type == HitlEntityType.PRODUCT.value
    assert decision.entity_id == product.id


def test_second_approve_on_draft_cannot_queue_outline_twice(
    no_celery_broker,
):
    product = _product(ProductStatus.DRAFT.value)
    _decide(product)  # status is now OUTLINING

    with pytest.raises(HTTPException) as exc_info:
        _decide(product)

    assert exc_info.value.status_code == 409
    assert len(no_celery_broker) == 1


def test_approve_outlined_moves_to_writing_and_queues_write(
    no_celery_broker,
):
    product = _product(ProductStatus.OUTLINED.value)

    _, result = _decide(product)

    assert result.status == ProductStatus.WRITING.value
    assert no_celery_broker == [(TaskName.EBOOK_WRITE, [str(product.id)])]


def test_task_is_queued_only_after_commit(monkeypatch):
    product = _product(ProductStatus.DRAFT.value)
    order: list[str] = []
    db = MagicMock()
    db.get.return_value = product
    db.commit.side_effect = lambda: order.append("commit")
    monkeypatch.setattr(
        "revenue_swarm.celery.celery_app.send_task",
        lambda *a, **k: order.append("send"),
    )

    decide_product(db, product.id, HitlDecisionValue.APPROVED, None)

    assert order == ["commit", "send"]


def test_assembled_without_review_cannot_go_live(no_celery_broker):
    product = _product(ProductStatus.ASSEMBLED.value)

    with pytest.raises(HTTPException) as exc_info:
        _decide(product)

    assert exc_info.value.status_code == 409
    assert product.status == ProductStatus.ASSEMBLED.value


def test_assembled_with_review_goes_live(no_celery_broker):
    product = _product(
        ProductStatus.ASSEMBLED.value,
        extras={"reviewed_at": "2026-10-13T01:00:00Z"},
    )

    _, result = _decide(product)

    assert result.status == ProductStatus.LIVE.value
    assert no_celery_broker == []


def test_review_requirement_can_be_disabled(monkeypatch, no_celery_broker):
    monkeypatch.setattr("app.services.hitl.EBOOK_MIN_HUMAN_REVIEW", False)
    product = _product(ProductStatus.ASSEMBLED.value)

    _, result = _decide(product)

    assert result.status == ProductStatus.LIVE.value


@pytest.mark.parametrize(
    "current_status",
    [
        ProductStatus.DRAFT.value,
        ProductStatus.OUTLINED.value,
        ProductStatus.ASSEMBLED.value,
    ],
)
def test_reject_archives_and_queues_nothing(current_status, no_celery_broker):
    product = _product(current_status)

    _, result = _decide(product, HitlDecisionValue.REJECTED)

    assert result.status == ProductStatus.ARCHIVED.value
    assert no_celery_broker == []


@pytest.mark.parametrize(
    "current_status",
    [
        ProductStatus.OUTLINING.value,
        ProductStatus.WRITING.value,
        ProductStatus.LIVE.value,
        ProductStatus.ARCHIVED.value,
    ],
)
@pytest.mark.parametrize("decision", list(HitlDecisionValue))
def test_in_flight_and_terminal_products_are_not_decidable(
    current_status, decision, no_celery_broker
):
    product = _product(current_status)
    db = MagicMock()
    db.get.return_value = product

    with pytest.raises(HTTPException) as exc_info:
        decide_product(db, product.id, decision, None)

    assert exc_info.value.status_code == 409
    db.commit.assert_not_called()
    assert no_celery_broker == []


def test_decide_product_raises_404_when_missing():
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        decide_product(db, uuid.uuid4(), HitlDecisionValue.APPROVED, None)

    assert exc_info.value.status_code == 404


def test_expected_status_mismatch_is_refused_without_side_effects(
    no_celery_broker,
):
    product = _product(ProductStatus.OUTLINED.value)
    db = MagicMock()
    db.get.return_value = product

    with pytest.raises(HTTPException) as exc_info:
        decide_product(
            db,
            product.id,
            HitlDecisionValue.APPROVED,
            None,
            expected_status=ProductStatus.DRAFT.value,
        )

    assert exc_info.value.status_code == 409
    assert product.status == ProductStatus.OUTLINED.value
    db.commit.assert_not_called()
    assert no_celery_broker == []


def test_expected_status_match_is_applied(no_celery_broker):
    product = _product(ProductStatus.DRAFT.value)
    db = MagicMock()
    db.get.return_value = product

    result = decide_product(
        db,
        product.id,
        HitlDecisionValue.APPROVED,
        None,
        expected_status=ProductStatus.DRAFT.value,
    )

    assert result.status == ProductStatus.OUTLINING.value

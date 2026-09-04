"""
Tests for `generate_paragraph_task` run directly (`.run(...)`),
bypassing the Celery/Redis broker — in production, the worker executes the
function itself anyway, the broker just delivers it there. Requires a real
Postgres: the task opens its own session via `SessionLocal()`, so it
uses the `real_session` fixture (see tests/conftest.py) instead of the
transactional `db_session`.
"""

import uuid

import app.services.llm as llm_module
import pytest
from app.models.task import AgentTask
from app.workers.tasks import generate_paragraph_task

pytestmark = pytest.mark.integration


def test_task_succeeds_and_stores_stub_output(real_session):
    task = AgentTask(
        type="generate_paragraph",
        status="queued",
        input={"prompt": "Describe a walking skeleton."},
    )
    real_session.add(task)
    real_session.commit()
    real_session.refresh(task)

    generate_paragraph_task.run(str(task.id))

    real_session.expire_all()
    updated = real_session.get(AgentTask, task.id)
    assert updated.status == "succeeded"
    assert updated.output == {"text": llm_module.STUB_TEXT}
    assert updated.error is None
    assert updated.started_at is not None
    assert updated.finished_at is not None


def test_task_uses_default_prompt_when_missing(real_session):
    task = AgentTask(type="generate_paragraph", status="queued", input={})
    real_session.add(task)
    real_session.commit()
    real_session.refresh(task)

    generate_paragraph_task.run(str(task.id))

    real_session.expire_all()
    updated = real_session.get(AgentTask, task.id)
    assert updated.status == "succeeded"


def test_task_marks_failure_and_reraises_on_llm_error(
    real_session, monkeypatch
):
    def _boom(prompt):
        raise RuntimeError("Ollama unavailable")

    monkeypatch.setattr("app.workers.tasks.generate_paragraph", _boom)

    task = AgentTask(
        type="generate_paragraph", status="queued", input={"prompt": "x"}
    )
    real_session.add(task)
    real_session.commit()
    real_session.refresh(task)

    with pytest.raises(RuntimeError, match="Ollama unavailable"):
        generate_paragraph_task.run(str(task.id))

    real_session.expire_all()
    updated = real_session.get(AgentTask, task.id)
    assert updated.status == "failed"
    assert updated.error == "Ollama unavailable"
    assert updated.finished_at is not None


def test_task_is_a_noop_for_unknown_task_id(real_session):
    # It shouldn't raise an exception
    # the task simply returns without doing anything.
    generate_paragraph_task.run(str(uuid.uuid4()))

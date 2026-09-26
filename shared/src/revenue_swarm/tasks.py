import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from revenue_swarm.db import SessionLocal
from revenue_swarm.models.task import AgentTask


class TaskName(StrEnum):
    GENERATE_PARAGRAPH = "generate_paragraph"
    RESEARCH_DISCOVER = "research.discover_programs"
    CONTENT_GENERATE = "content.generate"
    CONTENT_PUBLISH_DUE = "content.publish_due"


class Queue(StrEnum):
    DEFAULT = "celery"
    RESEARCH = "research"
    CONTENT = "content"


Handler = Callable[[Session, AgentTask], dict[str, object]]


def run_agent_task(task_id: str, handler: Handler) -> None:
    """Runs `handler` inside the standard agent-task lifecycle.

    Marks the row as running, stores whatever the handler returns in
    `output`, and on failure records the error before re-raising so Celery
    still sees the task as failed.
    """
    db = SessionLocal()
    try:
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.now(UTC)
        db.commit()

        row.output = handler(db, row)
        row.status = "succeeded"
        row.finished_at = datetime.now(UTC)
        row.error = None
        db.commit()
    except Exception as e:
        db.rollback()
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is not None:
            row.status = "failed"
            row.error = str(e)
            row.finished_at = datetime.now(UTC)
            db.commit()
        raise
    finally:
        db.close()

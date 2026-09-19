import uuid
from datetime import UTC, datetime

from app.agents.research.agent import discover_programs
from app.core.db import SessionLocal
from app.models.task import AgentTask
from app.workers.celery_app import celery_app


@celery_app.task(name="research.discover_programs")
def discover_programs_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.now(UTC)
        db.commit()

        limit = int(row.input.get("limit", 5))
        result = discover_programs(db, row.id, limit)

        row.output = result
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

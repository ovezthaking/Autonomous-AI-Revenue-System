import uuid
from datetime import UTC, datetime

from app.core.db import SessionLocal
from app.models.task import AgentTask
from app.services.llm import generate_paragraph
from app.workers.celery_app import celery_app


@celery_app.task(name="generate_paragraph")
def generate_paragraph_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        row = db.get(AgentTask, uuid.UUID(task_id))
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.now(UTC)
        db.commit()

        prompt = str(
            row.input.get(
                "prompt", "Write one short paragraph about walking skeletons."
            )
        )
        text = generate_paragraph(prompt)

        row.output = {"text": text}
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

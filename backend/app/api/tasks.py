import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.task import AgentTask
from app.schemas.task import TaskCreate, TaskRead
from app.workers.tasks import generate_paragraph_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
def create_task(body: TaskCreate, db: DbSession) -> AgentTask:
    row = AgentTask(
        type="generate_paragraph",
        status="queued",
        input={"prompt": body.prompt},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    generate_paragraph_task.delay(str(row.id))
    return row


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, db: DbSession) -> AgentTask:
    row = db.get(AgentTask, task_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return row

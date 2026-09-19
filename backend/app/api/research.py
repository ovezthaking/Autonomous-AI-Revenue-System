from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import TaskType
from app.models.task import AgentTask
from app.schemas.research import ResearchRunCreate
from app.schemas.task import TaskRead
from app.workers.research import discover_programs_task

router = APIRouter(prefix="/research", tags=["research"])
DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/run", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED
)
def run_research(
    db: DBSession, body: ResearchRunCreate | None = None
) -> AgentTask:
    limit = body.limit if body else 5
    row = AgentTask(
        type=TaskType.RESEARCH_PROGRAMS.value,
        status="queued",
        input={"limit": limit},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    discover_programs_task.delay(str(row.id))
    return row

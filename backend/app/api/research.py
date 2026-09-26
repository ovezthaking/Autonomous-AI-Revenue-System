from typing import Annotated

from fastapi import APIRouter, Depends, status
from revenue_swarm.celery import celery_app
from revenue_swarm.db import get_db
from revenue_swarm.enums import TaskType
from revenue_swarm.models.task import AgentTask
from revenue_swarm.tasks import TaskName
from sqlalchemy.orm import Session

from app.schemas.research import ResearchRunCreate
from app.schemas.task import TaskRead

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
    celery_app.send_task(TaskName.RESEARCH_DISCOVER, args=[str(row.id)])
    return row

from revenue_swarm.celery import celery_app
from revenue_swarm.tasks import TaskName, run_agent_task

from research_agent.agent import discover_programs_v1, discover_programs_v2
from research_agent.settings import RESEARCH_SOURCE


@celery_app.task(
    name=TaskName.RESEARCH_DISCOVER.value,
    soft_time_limit=600,
    time_limit=660,
)
def discover_programs_task(task_id: str) -> None:
    def handler(db, row):
        limit = int(row.input.get("limit", 10))
        if RESEARCH_SOURCE == "catalog":
            return discover_programs_v1(db, row.id, limit)
        return discover_programs_v2(db, row.id, limit)

    run_agent_task(task_id, handler)

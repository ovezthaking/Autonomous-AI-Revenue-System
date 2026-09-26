from revenue_swarm.celery import celery_app
from revenue_swarm.tasks import TaskName, run_agent_task

from research_agent.agent import discover_programs


@celery_app.task(name=TaskName.RESEARCH_DISCOVER.value)
def discover_programs_task(task_id: str) -> None:
    def handler(db, row):
        return discover_programs(db, row.id, int(row.input.get("limit", 5)))

    run_agent_task(task_id, handler)

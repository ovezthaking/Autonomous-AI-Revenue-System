from revenue_swarm.celery import celery_app
from revenue_swarm.llm import generate_paragraph
from revenue_swarm.tasks import TaskName, run_agent_task

DEFAULT_PROMPT = "Write one short paragraph about walking skeletons."


@celery_app.task(name=TaskName.GENERATE_PARAGRAPH.value)
def generate_paragraph_task(task_id: str) -> None:
    def handler(db, row):
        prompt = str(row.input.get("prompt", DEFAULT_PROMPT))
        return {"text": generate_paragraph(prompt)}

    run_agent_task(task_id, handler)

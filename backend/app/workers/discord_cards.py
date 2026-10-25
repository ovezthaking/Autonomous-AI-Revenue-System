import uuid

from app.services.discord_hitl import notify_proposed
from app.services.hitl_subject import subject_from_program
from revenue_swarm.celery import celery_app
from revenue_swarm.db import SessionLocal
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.tasks import TaskName


@celery_app.task(name=TaskName.DISCORD_NOTIFY_PROPOSED.value)
def notify_proposed_task(program_id: str) -> None:
    db = SessionLocal()
    try:
        row = db.get(AffiliateProgram, uuid.UUID(program_id))
        if row is None:
            return
        notify_proposed(db, subject_from_program(row))
    finally:
        db.close()

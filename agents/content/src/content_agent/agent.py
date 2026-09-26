import uuid

from revenue_swarm.enums import ContentChannel, ContentStatus, ProgramStatus
from revenue_swarm.llm import generate_copy
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_agent.templates import (
    BLOG_PROMPT,
    SOCIAL_PROMPT,
    STUB_BLOG,
    STUB_SOCIAL,
    render_blog,
    render_social,
)


def select_programs(db: Session, limit: int) -> list[AffiliateProgram]:
    already_has_content = (
        select(ContentItem.id)
        .where(ContentItem.affiliate_program_id == AffiliateProgram.id)
        .exists()
    )
    stmt = (
        select(AffiliateProgram)
        .where(
            AffiliateProgram.status == ProgramStatus.APPROVED.value,
            AffiliateProgram.affiliate_link.is_not(None),
            ~already_has_content,
        )
        .order_by(AffiliateProgram.updated_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _items_for(
    program: AffiliateProgram, task_id: uuid.UUID
) -> list[ContentItem]:
    context = {
        "name": program.name,
        "category": program.category or "business software",
        "commission": (program.extras or {}).get("commission", "n/a"),
    }
    link = program.affiliate_link or ""

    blog_body = generate_copy(BLOG_PROMPT.format(**context), stub=STUB_BLOG)
    social_body = generate_copy(
        SOCIAL_PROMPT.format(**context), stub=STUB_SOCIAL
    )

    common = {
        "affiliate_program_id": program.id,
        "status": ContentStatus.DRAFT.value,
        "source_task_id": task_id,
        "extras": {"generated_by": "content_agent_v1"},
    }
    return [
        ContentItem(
            title=f"{program.name} - review",
            body=render_blog(blog_body, program.name, link),
            channel=ContentChannel.BLOG.value,
            **common,
        ),
        ContentItem(
            title=f"{program.name} - social post",
            body=render_social(social_body, link),
            channel=ContentChannel.SOCIAL.value,
            **common,
        ),
    ]


def generate_content(
    db: Session, task_id: uuid.UUID, limit: int = 3
) -> dict[str, object]:
    programs = select_programs(db, limit)

    created: list[ContentItem] = []
    for program in programs:
        for item in _items_for(program, task_id):
            db.add(item)
            created.append(item)

    db.commit()
    for item in created:
        db.refresh(item)

    return {
        "programs": len(programs),
        "created": len(created),
        "content_ids": [str(item.id) for item in created],
    }

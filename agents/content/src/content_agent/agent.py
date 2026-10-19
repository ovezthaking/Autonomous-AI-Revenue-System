import uuid

from revenue_swarm.enums import (
    ApplicationStatus,
    ContentChannel,
    ContentStatus,
    ProgramStatus,
)
from revenue_swarm.links import link_for_content
from revenue_swarm.llm import generate_copy
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.content_item import ContentItem
from revenue_swarm.networks import PermanentNetworkError
from sqlalchemy import or_, select
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
    # Active programs get links from the network; others need a pasted one.
    can_link = or_(
        AffiliateProgram.application_status == ApplicationStatus.ACTIVE.value,
        AffiliateProgram.affiliate_link.is_not(None),
    )
    stmt = (
        select(AffiliateProgram)
        .where(
            AffiliateProgram.status == ProgramStatus.APPROVED.value,
            can_link,
            ~already_has_content,
        )
        .order_by(AffiliateProgram.updated_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _items_for(
    program: AffiliateProgram,
    task_id: uuid.UUID,
    db: Session | None = None,
) -> list[ContentItem]:
    """Builds blog and social drafts for a program.

    With `db`, items are flushed first so each gets its own tracked link
    (SubID = item id). Without it, the pasted `affiliate_link` is used.
    """
    context = {
        "name": program.name,
        "category": program.category or "business software",
        "commission": (program.extras or {}).get("commission", "n/a"),
    }

    blog_body = generate_copy(BLOG_PROMPT.format(**context), stub=STUB_BLOG)
    social_body = generate_copy(
        SOCIAL_PROMPT.format(**context), stub=STUB_SOCIAL
    )

    def common() -> dict[str, object]:
        return {
            "id": uuid.uuid4(),
            "affiliate_program_id": program.id,
            "status": ContentStatus.DRAFT.value,
            "source_task_id": task_id,
            "body": "",
            "extras": {"generated_by": "content_agent_v1"},
        }

    blog = ContentItem(
        title=f"{program.name} - review",
        channel=ContentChannel.BLOG.value,
        **common(),
    )
    social = ContentItem(
        title=f"{program.name} - social post",
        channel=ContentChannel.SOCIAL.value,
        **common(),
    )

    if db is None:
        blog_link = social_link = program.affiliate_link or ""
    else:
        db.add_all([blog, social])
        db.flush()
        blog_link = link_for_content(db, program, blog)
        social_link = link_for_content(db, program, social)
        for item, link in ((blog, blog_link), (social, social_link)):
            item.extras = {**(item.extras or {}), "affiliate_url": link}

    blog.body = render_blog(
        blog_body, program.name, blog_link, network=program.network
    )
    social.body = render_social(social_body, social_link)
    return [blog, social]


def generate_content(
    db: Session, task_id: uuid.UUID, limit: int = 3
) -> dict[str, object]:
    programs = select_programs(db, limit)

    created: list[ContentItem] = []
    skipped: list[dict[str, str]] = []
    for program in programs:
        try:
            with db.begin_nested():
                created.extend(_items_for(program, task_id, db))
        except PermanentNetworkError as exc:
            skipped.append({"program": program.name, "error": str(exc)})

    db.commit()
    for item in created:
        db.refresh(item)

    result: dict[str, object] = {
        "programs": len(programs),
        "created": len(created),
        "content_ids": [str(item.id) for item in created],
    }
    if skipped:
        result["skipped"] = skipped
    return result

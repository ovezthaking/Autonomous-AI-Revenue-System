import uuid

from app.agents.content.agent import _items_for
from app.core.enums import ContentStatus
from app.models.affiliate_program import AffiliateProgram


def test_social_item_shares_common_fields():
    program = AffiliateProgram(
        name="Example CRM",
        category="saas",
        extras={"commission": "20% recurring"},
        affiliate_link="https://aff.test/ref?id=1",
    )
    program.id = uuid.uuid4()
    task_id = uuid.uuid4()

    _blog, social = _items_for(program, task_id)

    assert social.affiliate_program_id == program.id
    assert social.status == ContentStatus.DRAFT.value
    assert social.source_task_id == task_id
    assert social.extras == {"generated_by": "content_agent_v1"}

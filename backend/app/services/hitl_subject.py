import uuid
from dataclasses import dataclass

from revenue_swarm.enums import HitlEntityType
from revenue_swarm.models.affiliate_program import AffiliateProgram


@dataclass(frozen=True)
class HitlSubject:
    entity_type: str
    entity_id: uuid.UUID
    label: str
    detail: str | None
    url: str | None
    status: str


def subject_from_program(row: AffiliateProgram) -> HitlSubject:
    return HitlSubject(
        entity_type=HitlEntityType.AFFILIATE_PROGRAM.value,
        entity_id=row.id,
        label=row.name,
        detail=row.rationale,
        url=row.url,
        status=row.status,
    )

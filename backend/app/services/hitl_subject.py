import uuid
from dataclasses import dataclass

from revenue_swarm.enums import HitlEntityType
from revenue_swarm.models.affiliate_program import AffiliateProgram
from revenue_swarm.models.product_idea import ProductIdea
from revenue_swarm.models.product_listing import ProductListing


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


def subject_from_idea(row: ProductIdea) -> HitlSubject:
    return HitlSubject(
        entity_type=HitlEntityType.PRODUCT_IDEA.value,
        entity_id=row.id,
        label=row.title,
        detail=f"Score: {row.score}",
        url=None,
        status=row.status,
    )


def subject_from_listing(row: ProductListing) -> HitlSubject:
    return HitlSubject(
        entity_type=HitlEntityType.SHOP_LISTING.value,
        entity_id=row.id,
        label=row.handle,
        detail=f"Platform: {row.platform}",
        url=None,
        status=row.status,
    )

from enums import StrEnum


class ProgramStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class HitlDecisionValue(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class HitlEntityType(StrEnum):
    AFFILIATE_PROGRAM = "affiliate_program"
    CONTENT_ITEM = "content_item"

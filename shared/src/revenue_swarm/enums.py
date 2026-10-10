from enum import StrEnum


class ProgramStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ContentChannel(StrEnum):
    BLOG = "blog"
    SOCIAL = "social"


class HitlDecisionValue(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class HitlEntityType(StrEnum):
    AFFILIATE_PROGRAM = "affiliate_program"
    CONTENT_ITEM = "content_item"
    PRODUCT = "product"


class TaskType(StrEnum):
    GENERATE_PARAGRAPH = "generate_paragraph"
    RESEARCH_PROGRAMS = "research_programs"
    GENERATE_CONTENT = "generate_content"
    PUBLISH_DUE = "publish_due"


class PublicationStatus(StrEnum):
    IN_FLIGHT = "in_flight"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    RETRACTED = "retracted"


class PublishTargetName(StrEnum):
    DRYRUN = "dryrun"
    WORDPRESS = "wordpress"
    MASTODON = "mastodon"
    X = "x"


class ProductStatus(StrEnum):
    DRAFT = "draft"
    OUTLINED = "outlined"
    WRITING = "writing"
    ASSEMBLED = "assembled"
    LIVE = "live"
    ARCHIVED = "archived"

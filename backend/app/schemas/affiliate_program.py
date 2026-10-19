import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    url: str | None = None
    network: str | None = None
    category: str | None = None
    rationale: str | None = None
    extras: dict[str, Any] | None = None


class HitlAction(BaseModel):
    comment: str | None = None


class RecommendationRead(BaseModel):
    id: uuid.UUID
    name: str
    url: str | None
    affiliate_link: str | None
    network: str | None
    category: str | None
    rationale: str | None
    extras: dict[str, Any] | None
    status: str
    score: float | None
    source_task_id: uuid.UUID | None
    network_program_id: str | None = None
    application_status: str = "not_applied"
    applied_at: datetime | None = None
    activated_at: datetime | None = None
    allow_redirect: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AffiliateLinkUpdate(BaseModel):
    affiliate_link: str = Field(min_length=8, max_length=2000)


class ProgramMetricsUpdate(BaseModel):
    epc: float = Field(gt=0, le=1000)
    epc_source: str = Field(default="network_dashboard", max_length=100)


class ActivateBody(BaseModel):
    network: str = Field(min_length=1, max_length=40)
    network_program_id: str | None = Field(default=None, max_length=80)


class AffiliateLinkRead(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    program_name: str | None = None
    content_item_id: uuid.UUID | None
    content_title: str | None = None
    destination_url: str
    tracking_url: str
    slug: str
    subid: str
    network: str
    status: str
    last_checked_at: datetime | None
    created_at: datetime


class LinkRepair(BaseModel):
    destination_url: str = Field(min_length=8, max_length=2000)

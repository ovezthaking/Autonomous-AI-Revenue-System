import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContentItemRead(BaseModel):
    id: uuid.UUID
    affiliate_program_id: uuid.UUID | None
    title: str
    body: str
    channel: str
    status: str
    source_task_id: uuid.UUID | None
    extras: dict[str, Any] | None
    scheduled_for: datetime | None
    published_at: datetime | None
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentRunCreate(BaseModel):
    limit: int = Field(default=3, ge=1, le=10)


class ContentSchedule(BaseModel):
    scheduled_for: datetime | None = None

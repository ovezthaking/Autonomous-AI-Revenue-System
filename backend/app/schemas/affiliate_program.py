from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field


class RecomendationCreate(BaseModel):
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
    network: str | None
    category: str | None
    rationale: str | None
    extras: dict[str, Any] = None
    status: str
    source_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

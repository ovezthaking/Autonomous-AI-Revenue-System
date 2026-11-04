import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProductIdeaRead(BaseModel):
    id: uuid.UUID
    term: str
    title: str
    kind: str
    score: float
    score_breakdown: dict[str, Any]
    status: str
    blocked_reason: str | None
    source_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListingRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    platform: str
    handle: str
    external_id: str | None
    external_variant_id: str | None
    status: str
    last_synced_at: datetime | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

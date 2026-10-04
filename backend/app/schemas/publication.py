import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PublicationRead(BaseModel):
    id: uuid.UUID
    content_item_id: uuid.UUID
    target: str
    status: str
    attempts: str
    external_id: str | None
    external_url: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResolvePublication(BaseModel):
    resolution: Literal["published", "not_published"]
    external_id: str | None = None
    external_url: str | None = None

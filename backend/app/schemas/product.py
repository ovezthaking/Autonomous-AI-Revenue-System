import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductRead(BaseModel):
    id: uuid.UUID
    kind: str
    slug: str
    title: str
    subtitle: str | None
    description: str | None
    price_cents: int
    currency: str
    status: str
    asset_pdf: str | None
    asset_epub: str | None
    extras: dict[str, Any] | None
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterRead(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    brief: str
    status: str
    error: str | None
    tokens_used: int | None

    model_config = {"from_attributes": True}


class ProductProposeCreate(BaseModel):
    niche: str = Field(min_length=1, max_length=200)


class ProductReview(BaseModel):
    reviewer: str = Field(min_length=1, max_length=200)

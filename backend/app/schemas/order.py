import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    consent_immediate_delivery: bool = True

    model_config = {"extra": "ignore"}


class OrderRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    provider: str
    provider_session_id: str
    provider_payment_id: str | None
    email: str | None
    amount_cents: int
    currency: str
    status: str
    consent_immediate_delivery: bool
    fulfilled_at: datetime | None
    extras: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

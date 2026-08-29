import uuid
from datetime import datetime

from pydantic import BaseModel


class ContentItemRead(BaseModel):
    id: uuid.UUID
    affiliate_program_id: uuid.UUID | None
    title: str
    body: str
    channel: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    prompt: str = Field(
        default="Write one short paragraph about a"
        "walking skeleton architecture.",
        min_length=1,
    )


class TaskRead(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}

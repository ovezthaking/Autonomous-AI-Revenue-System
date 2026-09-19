from pydantic import BaseModel, Field


class ResearchRunCreate(BaseModel):
    limit: int = Field(default=5, ge=1, le=15)

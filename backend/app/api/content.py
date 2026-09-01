from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content_item import ContentItem
from app.schemas.content_item import ContentItemRead


router = APIRouter(prefix="/content", tags=["content"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ContentItemRead])
def list_content(db: DbSession) -> list(ContentItem):
    stmt = select(ContentItem).order_by(ContentItem.created_at.desc())
    return list(db.scalars(stmt).all())

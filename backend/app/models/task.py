import uuid
import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.db import Base


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="queued"
    )

    input: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False
    )

    output: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=datetime.now(datetime.timezone.utc),
        default=datetime.now(datetime.timezone.utc)
    )

    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

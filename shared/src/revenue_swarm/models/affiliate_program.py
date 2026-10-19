import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from revenue_swarm.db import Base
from revenue_swarm.enums import ApplicationStatus, ProgramStatus


class AffiliateProgram(Base):
    __tablename__ = "affiliate_programs"
    __table_args__ = (
        # Amazon refuses commission on redirected clicks; enforce at write.
        CheckConstraint(
            "network IS DISTINCT FROM 'amazon' OR allow_redirect = false",
            name="ck_amazon_no_redirect",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    affiliate_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    network: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    extras: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=ProgramStatus.PROPOSED.value,
    )
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=True
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_program_id: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    application_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=ApplicationStatus.NOT_APPLIED.value,
        server_default=ApplicationStatus.NOT_APPLIED.value,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    allow_redirect: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

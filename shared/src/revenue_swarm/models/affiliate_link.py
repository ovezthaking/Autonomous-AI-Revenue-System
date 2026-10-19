import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revenue_swarm.db import Base
from revenue_swarm.enums import LinkStatus
from revenue_swarm.models.affiliate_program import AffiliateProgram


class AffiliateLink(Base):
    """One tracked link per (program, destination, content SubID)."""

    __tablename__ = "affiliate_links"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "destination_url",
            "subid",
            name="uq_affiliate_link",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("affiliate_programs.id"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=True
    )
    destination_url: Mapped[str] = mapped_column(Text, nullable=False)
    tracking_url: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    subid: Mapped[str] = mapped_column(Text, nullable=False)
    network: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=LinkStatus.ACTIVE.value
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    program: Mapped[AffiliateProgram] = relationship()

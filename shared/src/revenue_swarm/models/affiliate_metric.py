import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from revenue_swarm.db import Base


class AffiliateMetric(Base):
    __tablename__ = "affiliate_metrics"
    __table_args__ = (
        UniqueConstraint(
            "network",
            "program_id",
            "subid",
            "day",
            name="uq_metric_day",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    network: Mapped[str] = mapped_column(Text, nullable=False)
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affiliate_programs.id"),
        nullable=True,
    )
    subid: Mapped[str | None] = mapped_column(Text, nullable=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions_pending: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    conversions_approved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    conversions_declined: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    revenue_pending_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    revenue_approved_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

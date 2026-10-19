import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from revenue_swarm.db import Base


class LinkClick(Base):
    """Raw click on /go/{slug}.

    Deliberately no full IP and no raw User-Agent: a short hash and the
    country are enough for stats, and every extra field is a GDPR duty.
    """

    __tablename__ = "link_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affiliate_links.id"),
        nullable=False,
        index=True,
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    referer: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)

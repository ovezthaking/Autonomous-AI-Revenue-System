"""hitl discord messages

Revision ID: e3698b8201b0
Revises: a9b2c3d4e5f6
Create Date: 2026-10-25 00:48:57.038709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3698b8201b0'
down_revision: Union[str, Sequence[str], None] = 'a9b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hitl_discord_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            name="uq_hitl_discord_messages_entity",
        ),
    )


def downgrade() -> None:
    op.drop_table("hitl_discord_messages")

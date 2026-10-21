"""affiliate metrics

Revision ID: a9b2c3d4e5f6
Revises: f9a1c2d3e4b5
Create Date: 2026-10-20 01:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f9a1c2d3e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'affiliate_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('network', sa.Text(), nullable=False),
        sa.Column('program_id', sa.UUID(), nullable=True),
        sa.Column('subid', sa.Text(), nullable=True),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column(
            'conversions_pending',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
        sa.Column(
            'conversions_approved',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
        sa.Column(
            'conversions_declined',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
        sa.Column(
            'revenue_pending_cents',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
        sa.Column(
            'revenue_approved_cents',
            sa.Integer(),
            server_default='0',
            nullable=False,
        ),
        sa.Column(
            'currency', sa.Text(), server_default='USD', nullable=False
        ),
        sa.Column(
            'synced_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['program_id'], ['affiliate_programs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'network',
            'program_id',
            'subid',
            'day',
            name='uq_metric_day',
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.add_column('orders', sa.Column('source', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'source')
    op.drop_table('affiliate_metrics')

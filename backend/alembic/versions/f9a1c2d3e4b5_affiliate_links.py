"""affiliate links

Revision ID: f9a1c2d3e4b5
Revises: e1a2b3c4d5e6
Create Date: 2026-10-19 02:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f9a1c2d3e4b5'
down_revision: Union[str, Sequence[str], None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'affiliate_programs',
        sa.Column('network_program_id', sa.Text(), nullable=True),
    )
    op.add_column(
        'affiliate_programs',
        sa.Column(
            'application_status',
            sa.Text(),
            server_default='not_applied',
            nullable=False,
        ),
    )
    op.add_column(
        'affiliate_programs',
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'affiliate_programs',
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'affiliate_programs',
        sa.Column(
            'allow_redirect',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
        ),
    )
    # Existing Amazon rows must satisfy the constraint before it is added.
    op.execute(
        "UPDATE affiliate_programs SET allow_redirect = false "
        "WHERE network = 'amazon'"
    )
    op.create_check_constraint(
        'ck_amazon_no_redirect',
        'affiliate_programs',
        "network IS DISTINCT FROM 'amazon' OR allow_redirect = false",
    )

    op.create_table(
        'affiliate_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('program_id', sa.UUID(), nullable=False),
        sa.Column('content_item_id', sa.UUID(), nullable=True),
        sa.Column('destination_url', sa.Text(), nullable=False),
        sa.Column('tracking_url', sa.Text(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('subid', sa.Text(), nullable=False),
        sa.Column('network', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column(
            'last_checked_at', sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['program_id'], ['affiliate_programs.id']),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint(
            'program_id', 'destination_url', 'subid', name='uq_affiliate_link'
        ),
    )

    op.create_table(
        'link_clicks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('link_id', sa.UUID(), nullable=False),
        sa.Column(
            'clicked_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('referer', sa.Text(), nullable=True),
        sa.Column('user_agent_hash', sa.Text(), nullable=True),
        sa.Column('country', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['link_id'], ['affiliate_links.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_link_clicks_link_id'), 'link_clicks', ['link_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_link_clicks_link_id'), table_name='link_clicks')
    op.drop_table('link_clicks')
    op.drop_table('affiliate_links')
    op.drop_constraint(
        'ck_amazon_no_redirect', 'affiliate_programs', type_='check'
    )
    op.drop_column('affiliate_programs', 'allow_redirect')
    op.drop_column('affiliate_programs', 'activated_at')
    op.drop_column('affiliate_programs', 'applied_at')
    op.drop_column('affiliate_programs', 'application_status')
    op.drop_column('affiliate_programs', 'network_program_id')

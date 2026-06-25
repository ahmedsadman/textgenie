"""create bank_senders and bank_templates tables

Revision ID: d5e9c3b2a7f8
Revises: c4f8b2a1d5e6
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e9c3b2a7f8'
down_revision: Union[str, Sequence[str], None] = 'c4f8b2a1d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'bank_senders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bank_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['bank_id'], ['banks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bank_id', 'name', name='uq_bank_sender_name'),
    )

    op.create_table(
        'bank_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bank_id', sa.Integer(), nullable=False),
        sa.Column('template', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['bank_id'], ['banks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bank_templates')
    op.drop_table('bank_senders')

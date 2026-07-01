"""add paired_with_id to transactions

Revision ID: a1b2c3d4e5f6
Revises: e5a91c7d2f08
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e5a91c7d2f08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('paired_with_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_transactions_paired_with_id',
        'transactions',
        'transactions',
        ['paired_with_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_transactions_paired_with_id', 'transactions', type_='foreignkey'
    )
    op.drop_column('transactions', 'paired_with_id')

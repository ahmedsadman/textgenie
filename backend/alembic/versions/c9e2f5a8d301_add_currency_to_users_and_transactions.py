"""add currency to users and transactions

Revision ID: c9e2f5a8d301
Revises: b7d3e9f1a2c4
Create Date: 2026-07-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e2f5a8d301'
down_revision: Union[str, Sequence[str], None] = 'b7d3e9f1a2c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "normalized_currency",
            sa.String(length=3),
            nullable=False,
            server_default="BDT",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="BDT",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("transactions", "currency")
    op.drop_column("users", "normalized_currency")

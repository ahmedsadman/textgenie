"""add account_type and card_digits to banks

Revision ID: b7d3e9f1a2c4
Revises: a1b2c3d4e5f6
Create Date: 2026-07-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3e9f1a2c4'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "banks",
        sa.Column(
            "account_type",
            sa.String(length=16),
            nullable=False,
            server_default="deposit",
        ),
    )
    op.add_column(
        "banks",
        sa.Column("card_digits", sa.String(length=9), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("banks", "card_digits")
    op.drop_column("banks", "account_type")

"""rename tx amount/currency to normalized_ and add original_ columns

Revision ID: e1a37b04c8f2
Revises: c9e2f5a8d301
Create Date: 2026-07-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1a37b04c8f2"
down_revision: Union[str, Sequence[str], None] = "c9e2f5a8d301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "transactions",
        "amount",
        new_column_name="normalized_amount",
        existing_type=sa.Numeric(18, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "transactions",
        "currency",
        new_column_name="normalized_currency",
        existing_type=sa.String(length=3),
        existing_nullable=False,
        existing_server_default="BDT",
    )
    op.add_column(
        "transactions",
        sa.Column("original_amount", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("original_currency", sa.String(length=3), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("transactions", "original_currency")
    op.drop_column("transactions", "original_amount")
    op.alter_column(
        "transactions",
        "normalized_currency",
        new_column_name="currency",
        existing_type=sa.String(length=3),
        existing_nullable=False,
        existing_server_default="BDT",
    )
    op.alter_column(
        "transactions",
        "normalized_amount",
        new_column_name="amount",
        existing_type=sa.Numeric(18, 2),
        existing_nullable=False,
    )

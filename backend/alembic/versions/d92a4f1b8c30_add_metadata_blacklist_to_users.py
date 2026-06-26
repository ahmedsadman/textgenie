"""add metadata_blacklist to users

Revision ID: d92a4f1b8c30
Revises: f846c77c7c3d
Create Date: 2026-06-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd92a4f1b8c30'
down_revision: Union[str, Sequence[str], None] = 'f846c77c7c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("metadata_blacklist", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "metadata_blacklist")

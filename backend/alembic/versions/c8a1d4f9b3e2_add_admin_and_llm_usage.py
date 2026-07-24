"""add is_admin to users and create llm_usage table

Revision ID: c8a1d4f9b3e2
Revises: b5c2e8f0a4d7
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8a1d4f9b3e2'
down_revision: Union[str, Sequence[str], None] = 'b5c2e8f0a4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ADMIN_EMAIL = "ahmedsadman.211@gmail.com"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.execute(
        sa.text("UPDATE users SET is_admin = 1 WHERE email = :email").bindparams(
            email=ADMIN_EMAIL
        )
    )

    op.create_table(
        "llm_usage",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column(
            "input_tokens", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "cached_input_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "output_tokens", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "request_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "cost_micros", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "user_id", "usage_date", "provider", "model"
        ),
    )
    op.create_index(
        "ix_llm_usage_user_date", "llm_usage", ["user_id", "usage_date"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("llm_usage")
    op.drop_column("users", "is_admin")

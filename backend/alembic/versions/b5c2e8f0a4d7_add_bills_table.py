"""add bills table and transactions.bill_id

Revision ID: b5c2e8f0a4d7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5c2e8f0a4d7'
down_revision: Union[str, Sequence[str], None] = 'e1a37b04c8f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("normalized_total_due", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "normalized_currency",
            sa.String(3),
            nullable=False,
            server_default="BDT",
        ),
        sa.Column("original_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("original_currency", sa.String(3), nullable=True),
        sa.Column("statement_period", sa.Date(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["bank_id"], ["banks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("message_id", name="uq_bill_message_id"),
    )
    op.create_index("ix_bills_user_id", "bills", ["user_id"])
    op.create_index(
        "ix_bill_user_bank_period",
        "bills",
        ["user_id", "bank_id", "statement_period"],
    )

    op.add_column(
        "transactions",
        sa.Column("bill_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_bill_id",
        "transactions",
        "bills",
        ["bill_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_transaction_bill_id", "transactions", ["bill_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_transactions_bill_id", "transactions", type_="foreignkey"
    )
    op.drop_index("ix_transaction_bill_id", table_name="transactions")
    op.drop_column("transactions", "bill_id")

    # drop_table also drops the table's indexes; naming them explicitly
    # would fail on MySQL because they back FK constraints.
    op.drop_table("bills")

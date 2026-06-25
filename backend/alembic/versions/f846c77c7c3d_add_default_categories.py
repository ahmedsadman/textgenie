"""add default categories

Revision ID: f846c77c7c3d
Revises: c4f8b2a1d5e6
Create Date: 2026-06-25 17:44:23.157586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f846c77c7c3d'
down_revision: Union[str, Sequence[str], None] = 'c4f8b2a1d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_CATEGORIES = ("transaction", "bill")


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("categories", "user_id", existing_type=sa.Integer(), nullable=True)

    conn = op.get_bind()
    for name in _DEFAULT_CATEGORIES:
        conn.execute(
            sa.text("INSERT INTO categories (name, user_id) VALUES (:name, NULL)"),
            {"name": name},
        )
        global_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE name = :name AND user_id IS NULL"),
            {"name": name},
        ).scalar()

        old_ids = [
            row[0]
            for row in conn.execute(
                sa.text(
                    "SELECT id FROM categories WHERE name = :name AND user_id IS NOT NULL"
                ),
                {"name": name},
            ).fetchall()
        ]
        if old_ids:
            conn.execute(
                sa.text(
                    "UPDATE messages SET category_id = :global_id "
                    "WHERE category_id IN :old_ids"
                ),
                {"global_id": global_id, "old_ids": tuple(old_ids)},
            )
            conn.execute(
                sa.text("DELETE FROM categories WHERE id IN :old_ids"),
                {"old_ids": tuple(old_ids)},
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    for name in _DEFAULT_CATEGORIES:
        conn.execute(
            sa.text("DELETE FROM categories WHERE name = :name AND user_id IS NULL"),
            {"name": name},
        )
    op.alter_column("categories", "user_id", existing_type=sa.Integer(), nullable=False)

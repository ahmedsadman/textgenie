"""add webhook_token and messages table

Revision ID: b3f7a2c1d4e5
Revises: a81b913e26e1
Create Date: 2026-06-21 12:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f7a2c1d4e5'
down_revision: Union[str, Sequence[str], None] = 'a81b913e26e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('webhook_token', sa.String(length=36), nullable=True))

    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users WHERE webhook_token IS NULL"))
    for row in users:
        conn.execute(
            sa.text("UPDATE users SET webhook_token = :token WHERE id = :id"),
            {"token": str(uuid.uuid4()), "id": row[0]},
        )

    op.alter_column('users', 'webhook_token', existing_type=sa.String(length=36), nullable=False)
    op.create_index('ix_users_webhook_token', 'users', ['webhook_token'], unique=True)

    op.create_table('messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.execute("CREATE FULLTEXT INDEX ft_messages_sender_content ON messages (sender, content)")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('messages')
    op.drop_index('ix_users_webhook_token', table_name='users')
    op.drop_column('users', 'webhook_token')

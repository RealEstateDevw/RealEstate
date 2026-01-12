"""add_instagram_settings_table

Revision ID: 9e0be0ff02b2
Revises: 5b6fb3a0e2c4
Create Date: 2025-12-03 17:09:14.711196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e0be0ff02b2'
down_revision: Union[str, None] = '5b6fb3a0e2c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Проверяем, существует ли таблица
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='instagram_settings'"
    )).fetchone()

    if result is None:
        # Создаём таблицу instagram_settings только если она не существует
        op.create_table('instagram_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(), nullable=False),
        sa.Column('app_secret', sa.String(), nullable=False),
        sa.Column('redirect_uri', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    # Пропускаем alter_column для SQLite (не поддерживается)
    # и drop_table для lost_and_found (служебная таблица SQLite)


def downgrade() -> None:
    op.drop_table('instagram_settings')

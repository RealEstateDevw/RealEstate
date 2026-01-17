"""Remove Instagram integration tables

Revision ID: remove_instagram_001
Revises: ae25742f11fe
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_instagram_001'
down_revision: Union[str, None] = 'ae25742f11fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop Instagram tables
    op.drop_table('instagram_integrations')
    op.drop_table('instagram_settings')


def downgrade() -> None:
    # Recreate instagram_settings table
    op.create_table('instagram_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(), nullable=False),
        sa.Column('app_secret', sa.String(), nullable=False),
        sa.Column('redirect_uri', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate instagram_integrations table
    op.create_table('instagram_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('instagram_user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('account_type', sa.String(), nullable=True),
        sa.Column('media_count', sa.Integer(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instagram_user_id')
    )
    op.create_index('ix_instagram_integrations_user_id', 'instagram_integrations', ['user_id'], unique=False)

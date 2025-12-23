"""Bind instagram integrations to admin user

Revision ID: c82f4c6b8a93
Revises: bc9db8bc074b
Create Date: 2025-03-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c82f4c6b8a93'
down_revision = 'bc9db8bc074b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instagram_integrations') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_instagram_integrations_user_id_users',
            'users',
            ['user_id'],
            ['id'],
        )
        batch_op.create_index(
            'ix_instagram_integrations_user_id',
            ['user_id'],
            unique=False,
        )

    conn = op.get_bind()
    admin_id = conn.execute(
        sa.text(
            """
            SELECT u.id
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = :role
            ORDER BY u.id ASC
            LIMIT 1
            """
        ),
        {"role": "Админ"},
    ).scalar()
    if admin_id is not None:
        conn.execute(
            sa.text(
                "UPDATE instagram_integrations SET user_id = :uid WHERE user_id IS NULL"
            ),
            {"uid": admin_id},
        )


def downgrade():
    with op.batch_alter_table('instagram_integrations') as batch_op:
        batch_op.drop_index('ix_instagram_integrations_user_id')
        batch_op.drop_constraint('fk_instagram_integrations_user_id_users', type_='foreignkey')
        batch_op.drop_column('user_id')

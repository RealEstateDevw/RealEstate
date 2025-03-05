"""Photo commit

Revision ID: bc9db8bc074b
Revises: 6145bd71b260
Create Date: 2025-03-05 20:02:52.866122

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc9db8bc074b'
down_revision = '6145bd71b260'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode to modify the `check_photos` table
    with op.batch_alter_table('check_photos') as batch_op:
        # Drop the specified columns
        batch_op.drop_column('photo')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('lead_id')

        # Add the new foreign key constraint
        batch_op.create_foreign_key(
            'fk_check_photos_expense_id_expenses',
            'expenses',
            ['expense_id'],
            ['id']
        )


def downgrade():
    # Use batch mode to revert the changes to the `check_photos` table
    with op.batch_alter_table('check_photos') as batch_op:
        # Drop the new foreign key constraint
        batch_op.drop_constraint('fk_check_photos_expense_id_expenses', type_='foreignkey')

        # Add the dropped columns back
        batch_op.add_column(sa.Column('lead_id', sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('photo', sa.VARCHAR(), nullable=False))

        # Recreate the old foreign key constraint
        batch_op.create_foreign_key(
            'fk_check_photos_lead_id_leads_prototype',
            'leads_prototype',
            ['lead_id'],
            ['id']
        )
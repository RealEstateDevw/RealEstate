"""sql5 commit

Revision ID: 213fd73b5b3c
Revises: 1b74b4b1943b
Create Date: 2025-05-14 05:17:12.680965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '213fd73b5b3c'
down_revision: Union[str, None] = '1b74b4b1943b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('leads_prototype') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=True)


def downgrade():
    with op.batch_alter_table('leads_prototype') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=False)
    # ### end Alembic commands ###

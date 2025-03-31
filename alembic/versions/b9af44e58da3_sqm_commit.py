"""sqm commit

Revision ID: b9af44e58da3
Revises: f2c3a2de5189
Create Date: 2025-03-31 18:42:25.344005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9af44e58da3'
down_revision: Union[str, None] = 'f2c3a2de5189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала обновляем существующие NULL значения значением по умолчанию
    op.execute("UPDATE expenses SET category = 'Unknown' WHERE category IS NULL")

    # Затем делаем столбец NOT NULL с использованием batch_alter_table
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.alter_column('category',
                              existing_type=sa.VARCHAR(length=9),
                              nullable=False)

    with op.batch_alter_table('leads_prototype', schema=None) as batch_op:
        batch_op.alter_column('square_meters',
                              existing_type=sa.INTEGER(),
                              type_=sa.Float(),
                              existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('leads_prototype', schema=None) as batch_op:
        batch_op.alter_column('square_meters',
                              existing_type=sa.Float(),
                              type_=sa.INTEGER(),
                              existing_nullable=True)

    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.alter_column('category',
                              existing_type=sa.VARCHAR(length=9),
                              nullable=True)
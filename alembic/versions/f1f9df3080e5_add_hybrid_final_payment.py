"""add hybrid final payment field to leads

Revision ID: f1f9df3080e5
Revises: e8314a50ead1
Create Date: 2024-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1f9df3080e5'
down_revision: Union[str, None] = '7eefce3ffaeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads_prototype', sa.Column('hybrid_final_payment', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads_prototype', 'hybrid_final_payment')

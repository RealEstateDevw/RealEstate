"""Merge instagram user binding and hybrid payment branches

Revision ID: 5b6fb3a0e2c4
Revises: c82f4c6b8a93, f1f9df3080e5
Create Date: 2025-03-10 12:10:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b6fb3a0e2c4'
down_revision: Union[str, Sequence[str], None] = ('c82f4c6b8a93', 'f1f9df3080e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merge revision, no-op
    pass


def downgrade() -> None:
    # merge revision, no-op
    pass

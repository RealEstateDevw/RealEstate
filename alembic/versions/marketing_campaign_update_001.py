"""Update Campaign model and add campaign_id to Lead

Revision ID: marketing_campaign_001
Revises: remove_instagram_001
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'marketing_campaign_001'
down_revision: Union[str, None] = 'remove_instagram_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to campaigns table
    op.add_column('campaigns', sa.Column('utm_source', sa.String(), nullable=True))
    op.add_column('campaigns', sa.Column('utm_medium', sa.String(), nullable=True))
    op.add_column('campaigns', sa.Column('utm_campaign', sa.String(), nullable=True))
    op.add_column('campaigns', sa.Column('utm_link', sa.String(), nullable=True))
    op.add_column('campaigns', sa.Column('target_url', sa.String(), nullable=True))

    # Create unique index on utm_source
    op.create_index('ix_campaigns_utm_source', 'campaigns', ['utm_source'], unique=True)

    # Make account nullable
    op.alter_column('campaigns', 'account',
                    existing_type=sa.String(),
                    nullable=True)

    # Make end_date nullable
    op.alter_column('campaigns', 'end_date',
                    existing_type=sa.Date(),
                    nullable=True)

    # Add campaign_id to leads_prototype
    op.add_column('leads_prototype', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_leads_prototype_campaign_id', 'leads_prototype', ['campaign_id'])
    op.create_foreign_key(
        'fk_leads_prototype_campaign_id',
        'leads_prototype',
        'campaigns',
        ['campaign_id'],
        ['id']
    )


def downgrade() -> None:
    # Remove campaign_id from leads_prototype
    op.drop_constraint('fk_leads_prototype_campaign_id', 'leads_prototype', type_='foreignkey')
    op.drop_index('ix_leads_prototype_campaign_id', table_name='leads_prototype')
    op.drop_column('leads_prototype', 'campaign_id')

    # Make end_date not nullable
    op.alter_column('campaigns', 'end_date',
                    existing_type=sa.Date(),
                    nullable=False)

    # Make account not nullable
    op.alter_column('campaigns', 'account',
                    existing_type=sa.String(),
                    nullable=False)

    # Remove UTM columns from campaigns
    op.drop_index('ix_campaigns_utm_source', table_name='campaigns')
    op.drop_column('campaigns', 'target_url')
    op.drop_column('campaigns', 'utm_link')
    op.drop_column('campaigns', 'utm_campaign')
    op.drop_column('campaigns', 'utm_medium')
    op.drop_column('campaigns', 'utm_source')

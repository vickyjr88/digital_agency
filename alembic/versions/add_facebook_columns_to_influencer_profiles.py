"""add facebook columns to influencer_profiles

Revision ID: add_facebook_columns
Revises: add_payment_reference
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_facebook_columns'
down_revision = 'add_payment_reference'
branch_labels = None
depends_on = None


def upgrade():
    # Add Facebook-related columns to influencer_profiles table
    op.add_column('influencer_profiles', sa.Column('facebook_handle', sa.String(100), nullable=True))
    op.add_column('influencer_profiles', sa.Column('facebook_id', sa.String(100), nullable=True))
    op.add_column('influencer_profiles', sa.Column('facebook_followers', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('influencer_profiles', sa.Column('facebook_engagement_rate', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('influencer_profiles', sa.Column('facebook_verified', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('influencer_profiles', sa.Column('facebook_connected_at', sa.DateTime(), nullable=True))
    op.add_column('influencer_profiles', sa.Column('facebook_access_token', sa.String(500), nullable=True))
    op.add_column('influencer_profiles', sa.Column('facebook_link', sa.String(500), nullable=True))


def downgrade():
    # Remove Facebook-related columns from influencer_profiles table
    op.drop_column('influencer_profiles', 'facebook_link')
    op.drop_column('influencer_profiles', 'facebook_access_token')
    op.drop_column('influencer_profiles', 'facebook_connected_at')
    op.drop_column('influencer_profiles', 'facebook_verified')
    op.drop_column('influencer_profiles', 'facebook_engagement_rate')
    op.drop_column('influencer_profiles', 'facebook_followers')
    op.drop_column('influencer_profiles', 'facebook_id')
    op.drop_column('influencer_profiles', 'facebook_handle')

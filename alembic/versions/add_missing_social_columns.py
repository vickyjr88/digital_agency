"""add missing social columns to influencer_profiles

Revision ID: add_missing_social_columns
Revises: add_facebook_columns
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_social_columns'
down_revision = 'add_facebook_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing social media link columns and whatsapp_number to influencer_profiles table (idempotent)
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('influencer_profiles')]

    if 'whatsapp_number' not in columns:
        op.add_column('influencer_profiles', sa.Column('whatsapp_number', sa.String(20), nullable=True))
    if 'instagram_link' not in columns:
        op.add_column('influencer_profiles', sa.Column('instagram_link', sa.String(500), nullable=True))
    if 'tiktok_link' not in columns:
        op.add_column('influencer_profiles', sa.Column('tiktok_link', sa.String(500), nullable=True))
    if 'youtube_link' not in columns:
        op.add_column('influencer_profiles', sa.Column('youtube_link', sa.String(500), nullable=True))
    if 'twitter_link' not in columns:
        op.add_column('influencer_profiles', sa.Column('twitter_link', sa.String(500), nullable=True))


def downgrade():
    # Remove the columns
    op.drop_column('influencer_profiles', 'twitter_link')
    op.drop_column('influencer_profiles', 'youtube_link')
    op.drop_column('influencer_profiles', 'tiktok_link')
    op.drop_column('influencer_profiles', 'instagram_link')
    op.drop_column('influencer_profiles', 'whatsapp_number')

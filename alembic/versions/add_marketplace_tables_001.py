"""Add marketplace tables and user_type column

This migration adds:
1. user_type column to users table (brand/influencer/admin)
2. influencer_profiles table
3. packages table
4. wallets table
5. wallet_transactions table
6. escrow_holds table
7. campaigns table
8. deliverables table
9. reviews table
10. disputes table
11. notifications table

Revision ID: add_marketplace_tables_001
Revises: 
Create Date: 2026-01-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_marketplace_tables_001'
down_revision = None  # Set this to the previous migration's revision ID
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add user_type column to users table
    op.add_column('users', 
        sa.Column('user_type', 
                  sa.Enum('brand', 'influencer', 'admin', name='usertype'),
                  nullable=True, 
                  server_default='brand')
    )
    
    # Update existing users to have user_type = 'brand' (or 'admin' if role is admin)
    op.execute("""
        UPDATE users 
        SET user_type = CASE 
            WHEN role = 'admin' THEN 'admin'::usertype 
            ELSE 'brand'::usertype 
        END
        WHERE user_type IS NULL
    """)

    # 2. Create influencer_profiles table
    op.create_table('influencer_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        
        # Basic info
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('bio', sa.Text),
        sa.Column('profile_picture_url', sa.String(500)),
        sa.Column('niche', sa.String(100), nullable=False),
        sa.Column('location', sa.String(100)),
        
        # Instagram
        sa.Column('instagram_handle', sa.String(100)),
        sa.Column('instagram_id', sa.String(100)),
        sa.Column('instagram_followers', sa.Integer, default=0),
        sa.Column('instagram_engagement_rate', sa.Float, default=0.0),
        sa.Column('instagram_verified', sa.Boolean, default=False),
        sa.Column('instagram_connected_at', sa.DateTime),
        sa.Column('instagram_access_token', sa.String(500)),
        
        # TikTok
        sa.Column('tiktok_handle', sa.String(100)),
        sa.Column('tiktok_id', sa.String(100)),
        sa.Column('tiktok_followers', sa.Integer, default=0),
        sa.Column('tiktok_engagement_rate', sa.Float, default=0.0),
        sa.Column('tiktok_verified', sa.Boolean, default=False),
        sa.Column('tiktok_connected_at', sa.DateTime),
        sa.Column('tiktok_access_token', sa.String(500)),
        
        # YouTube
        sa.Column('youtube_channel', sa.String(100)),
        sa.Column('youtube_id', sa.String(100)),
        sa.Column('youtube_subscribers', sa.Integer, default=0),
        sa.Column('youtube_engagement_rate', sa.Float, default=0.0),
        sa.Column('youtube_verified', sa.Boolean, default=False),
        sa.Column('youtube_connected_at', sa.DateTime),
        sa.Column('youtube_access_token', sa.String(500)),
        
        # Twitter
        sa.Column('twitter_handle', sa.String(100)),
        sa.Column('twitter_id', sa.String(100)),
        sa.Column('twitter_followers', sa.Integer, default=0),
        sa.Column('twitter_engagement_rate', sa.Float, default=0.0),
        sa.Column('twitter_verified', sa.Boolean, default=False),
        sa.Column('twitter_connected_at', sa.DateTime),
        sa.Column('twitter_access_token', sa.String(500)),
        
        # Reputation
        sa.Column('rating', sa.Float, default=0.0),
        sa.Column('review_count', sa.Integer, default=0),
        sa.Column('completed_campaigns', sa.Integer, default=0),
        
        # Verification
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('verification_status', sa.Enum('pending', 'approved', 'rejected', name='verificationstatus'), default='pending'),
        sa.Column('identity_verified_at', sa.DateTime),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_influencer_user', 'influencer_profiles', ['user_id'])
    op.create_index('idx_influencer_niche', 'influencer_profiles', ['niche'])
    op.create_index('idx_influencer_rating', 'influencer_profiles', ['rating'])

    # 3. Create packages table
    op.create_table('packages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('platform', sa.Enum('instagram', 'tiktok', 'youtube', 'twitter', 'multi', name='platformtype'), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('deliverables_count', sa.Integer, nullable=False, default=1),
        sa.Column('price', sa.Integer, nullable=False),
        sa.Column('currency', sa.String(3), default='KES'),
        sa.Column('timeline_days', sa.Integer, nullable=False),
        sa.Column('revisions_included', sa.Integer, default=2),
        
        sa.Column('requirements', sa.JSON),
        sa.Column('exclusions', sa.Text),
        
        sa.Column('status', sa.Enum('active', 'paused', 'deleted', name='packagestatus'), default='active'),
        sa.Column('times_purchased', sa.Integer, default=0),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_packages_influencer', 'packages', ['influencer_id'])
    op.create_index('idx_packages_platform', 'packages', ['platform'])
    op.create_index('idx_packages_price', 'packages', ['price'])
    op.create_index('idx_packages_status', 'packages', ['status'])

    # 4. Create wallets table
    op.create_table('wallets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        
        sa.Column('balance', sa.Integer, default=0),
        sa.Column('hold_balance', sa.Integer, default=0),
        sa.Column('total_earned', sa.Integer, default=0),
        sa.Column('total_spent', sa.Integer, default=0),
        sa.Column('currency', sa.String(3), default='KES'),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_wallets_user', 'wallets', ['user_id'])

    # 5. Create wallet_transactions table
    op.create_table('wallet_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('from_wallet_id', sa.String(36), sa.ForeignKey('wallets.id'), nullable=True),
        sa.Column('to_wallet_id', sa.String(36), sa.ForeignKey('wallets.id'), nullable=True),
        
        sa.Column('amount', sa.Integer, nullable=False),
        sa.Column('fee', sa.Integer, default=0),
        sa.Column('net_amount', sa.Integer, nullable=False),
        
        sa.Column('transaction_type', sa.Enum('deposit', 'withdrawal', 'escrow_lock', 'escrow_release', 'escrow_refund', 'platform_fee', 'transfer', name='transactiontype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', name='transactionstatus'), default='pending'),
        
        sa.Column('payment_method', sa.String(30)),
        sa.Column('external_id', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('metadata_json', sa.JSON),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
    )
    op.create_index('idx_transactions_from_wallet', 'wallet_transactions', ['from_wallet_id'])
    op.create_index('idx_transactions_to_wallet', 'wallet_transactions', ['to_wallet_id'])
    op.create_index('idx_transactions_status', 'wallet_transactions', ['status'])
    op.create_index('idx_transactions_type', 'wallet_transactions', ['transaction_type'])

    # 6. Create campaigns table (before escrow_holds due to FK)
    op.create_table('campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('brand_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id'), nullable=False),
        sa.Column('package_id', sa.String(36), sa.ForeignKey('packages.id'), nullable=False),
        sa.Column('escrow_id', sa.String(36), nullable=True),  # FK added later
        
        sa.Column('brief', sa.JSON),
        sa.Column('custom_requirements', sa.Text),
        
        sa.Column('status', sa.Enum('pending', 'accepted', 'in_progress', 'draft_submitted', 'revision_requested', 'draft_approved', 'published', 'pending_review', 'completed', 'disputed', 'cancelled', name='campaignstatus'), default='pending'),
        
        sa.Column('deadline', sa.DateTime),
        sa.Column('started_at', sa.DateTime),
        sa.Column('draft_submitted_at', sa.DateTime),
        sa.Column('published_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        
        sa.Column('revisions_used', sa.Integer, default=0),
        sa.Column('revisions_allowed', sa.Integer),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_campaigns_brand', 'campaigns', ['brand_id'])
    op.create_index('idx_campaigns_influencer', 'campaigns', ['influencer_id'])
    op.create_index('idx_campaigns_status', 'campaigns', ['status'])
    op.create_index('idx_campaigns_deadline', 'campaigns', ['deadline'])

    # 7. Create escrow_holds table
    op.create_table('escrow_holds',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('transaction_id', sa.String(36), sa.ForeignKey('wallet_transactions.id'), nullable=False),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=True),
        
        sa.Column('amount', sa.Integer, nullable=False),
        sa.Column('status', sa.Enum('locked', 'released', 'refunded', 'disputed', name='escrowstatus'), default='locked'),
        
        sa.Column('locked_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('auto_release_at', sa.DateTime),
        sa.Column('released_at', sa.DateTime),
        
        sa.Column('release_transaction_id', sa.String(36), sa.ForeignKey('wallet_transactions.id'), nullable=True),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_escrow_campaign', 'escrow_holds', ['campaign_id'])
    op.create_index('idx_escrow_status', 'escrow_holds', ['status'])

    # Add FK from campaigns to escrow_holds
    op.create_foreign_key('fk_campaigns_escrow', 'campaigns', 'escrow_holds', ['escrow_id'], ['id'])

    # 8. Create deliverables table
    op.create_table('deliverables',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('platform', sa.Enum('instagram', 'tiktok', 'youtube', 'twitter', 'multi', name='platformtype', create_type=False), nullable=False),
        
        sa.Column('draft_url', sa.String(500)),
        sa.Column('draft_description', sa.Text),
        sa.Column('draft_caption', sa.Text),
        sa.Column('draft_media_urls', sa.JSON),
        
        sa.Column('published_url', sa.String(500)),
        sa.Column('published_at', sa.DateTime),
        sa.Column('verified_at', sa.DateTime),
        
        sa.Column('status', sa.Enum('pending', 'draft', 'submitted', 'approved', 'rejected', 'published', 'verified', name='deliverablestatus'), default='pending'),
        
        sa.Column('views', sa.Integer),
        sa.Column('likes', sa.Integer),
        sa.Column('comments', sa.Integer),
        sa.Column('shares', sa.Integer),
        sa.Column('engagement_rate', sa.Float),
        sa.Column('metrics_updated_at', sa.DateTime),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_deliverables_campaign', 'deliverables', ['campaign_id'])
    op.create_index('idx_deliverables_status', 'deliverables', ['status'])

    # 9. Create reviews table
    op.create_table('reviews',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewee_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('comment', sa.Text),
        sa.Column('response', sa.Text),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.UniqueConstraint('campaign_id', 'reviewer_id', name='uq_review_campaign_reviewer'),
    )
    op.create_index('idx_reviews_campaign', 'reviews', ['campaign_id'])
    op.create_index('idx_reviews_reviewee', 'reviews', ['reviewee_id'])

    # 10. Create disputes table
    op.create_table('disputes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raised_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('evidence_urls', sa.JSON),
        
        sa.Column('status', sa.Enum('open', 'under_review', 'resolved', 'closed', name='disputestatus'), default='open'),
        
        sa.Column('resolution', sa.Text),
        sa.Column('resolved_in_favor_of', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('resolved_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('resolved_at', sa.DateTime),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_disputes_campaign', 'disputes', ['campaign_id'])
    op.create_index('idx_disputes_status', 'disputes', ['status'])

    # 11. Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text),
        sa.Column('data', sa.JSON),
        
        sa.Column('read', sa.Boolean, default=False),
        sa.Column('read_at', sa.DateTime),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_notifications_user', 'notifications', ['user_id'])
    op.create_index('idx_notifications_read', 'notifications', ['user_id', 'read'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('notifications')
    op.drop_table('disputes')
    op.drop_table('reviews')
    op.drop_table('deliverables')
    
    # Remove FK before dropping escrow_holds
    op.drop_constraint('fk_campaigns_escrow', 'campaigns', type_='foreignkey')
    op.drop_table('escrow_holds')
    
    op.drop_table('campaigns')
    op.drop_table('wallet_transactions')
    op.drop_table('wallets')
    op.drop_table('packages')
    op.drop_table('influencer_profiles')
    
    # Drop user_type column
    op.drop_column('users', 'user_type')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS usertype")
    op.execute("DROP TYPE IF EXISTS verificationstatus")
    op.execute("DROP TYPE IF EXISTS platformtype")
    op.execute("DROP TYPE IF EXISTS packagestatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS escrowstatus")
    op.execute("DROP TYPE IF EXISTS campaignstatus")
    op.execute("DROP TYPE IF EXISTS deliverablestatus")
    op.execute("DROP TYPE IF EXISTS disputestatus")

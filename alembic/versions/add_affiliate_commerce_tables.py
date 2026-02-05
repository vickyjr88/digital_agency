"""Add affiliate commerce tables

Revision ID: affiliate_commerce_001
Revises: fix_campaign_status_enum
Create Date: 2025-02-05 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'affiliate_commerce_001'
down_revision = 'fix_campaign_status_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    commissiontypedb = postgresql.ENUM('percentage', 'fixed', name='commissiontypedb', create_type=True)
    commissiontypedb.create(op.get_bind(), checkfirst=True)

    productstatusdb = postgresql.ENUM('active', 'paused', 'archived', name='productstatusdb', create_type=True)
    productstatusdb.create(op.get_bind(), checkfirst=True)

    affiliateapprovalstatusdb = postgresql.ENUM('pending', 'approved', 'rejected', name='affiliateapprovalstatusdb', create_type=True)
    affiliateapprovalstatusdb.create(op.get_bind(), checkfirst=True)

    orderstatusdb = postgresql.ENUM('pending', 'contacted', 'in_progress', 'fulfilled', 'cancelled', name='orderstatusdb', create_type=True)
    orderstatusdb.create(op.get_bind(), checkfirst=True)

    commissionstatusdb = postgresql.ENUM('pending', 'paid', 'cancelled', name='commissionstatusdb', create_type=True)
    commissionstatusdb.create(op.get_bind(), checkfirst=True)

    preferredcontactmethoddb = postgresql.ENUM('whatsapp', 'phone', 'email', name='preferredcontactmethoddb', create_type=True)
    preferredcontactmethoddb.create(op.get_bind(), checkfirst=True)

    platformfeetypedb = postgresql.ENUM('percentage', 'fixed', name='platformfeetypedb', create_type=True)
    platformfeetypedb.create(op.get_bind(), checkfirst=True)

    # Create brand_profiles table
    op.create_table(
        'brand_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('brand_id', sa.String(36), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=True),
        sa.Column('whatsapp_number', sa.String(20), nullable=False),
        sa.Column('business_location', sa.Text(), nullable=False),
        sa.Column('business_hours', sa.String(200)),
        sa.Column('preferred_contact_method', sa.Enum('whatsapp', 'phone', 'email', name='preferredcontactmethoddb'), server_default='whatsapp'),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('business_email', sa.String(255)),
        sa.Column('website_url', sa.String(500)),
        sa.Column('instagram_handle', sa.String(100)),
        sa.Column('facebook_page', sa.String(200)),
        sa.Column('business_description', sa.Text()),
        sa.Column('business_category', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('auto_approve_influencers', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('ix_brand_profiles_user_id', 'brand_profiles', ['user_id'])

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('brand_profile_id', sa.String(36), sa.ForeignKey('brand_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('compare_at_price', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='KES'),
        sa.Column('commission_type', sa.Enum('percentage', 'fixed', name='commissiontypedb'), nullable=False, server_default='percentage'),
        sa.Column('commission_rate', sa.Numeric(5, 2)),
        sa.Column('fixed_commission', sa.Numeric(10, 2)),
        sa.Column('platform_fee_type', sa.Enum('percentage', 'fixed', name='platformfeetypedb'), nullable=False, server_default='percentage'),
        sa.Column('platform_fee_rate', sa.Numeric(5, 2), server_default='10.00'),
        sa.Column('platform_fee_fixed', sa.Numeric(10, 2)),
        sa.Column('in_stock', sa.Boolean(), server_default='true'),
        sa.Column('stock_quantity', sa.Integer()),
        sa.Column('track_inventory', sa.Boolean(), server_default='false'),
        sa.Column('images', sa.JSON()),
        sa.Column('thumbnail', sa.String(500)),
        sa.Column('video_url', sa.String(500)),
        sa.Column('has_variants', sa.Boolean(), server_default='false'),
        sa.Column('requires_shipping', sa.Boolean(), server_default='true'),
        sa.Column('weight', sa.Numeric(8, 2)),
        sa.Column('dimensions', sa.JSON()),
        sa.Column('auto_approve', sa.Boolean(), server_default='false'),
        sa.Column('approval_criteria', sa.JSON()),
        sa.Column('tags', sa.JSON()),
        sa.Column('status', sa.Enum('active', 'paused', 'archived', name='productstatusdb'), server_default='active'),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('total_clicks', sa.Integer(), server_default='0'),
        sa.Column('total_orders', sa.Integer(), server_default='0'),
        sa.Column('total_sales_amount', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('active_affiliates_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('ix_products_slug', 'products', ['slug'])
    op.create_index('ix_products_brand_profile_id', 'products', ['brand_profile_id'])
    op.create_index('ix_products_status', 'products', ['status'])
    op.create_index('ix_products_category', 'products', ['category'])

    # Create product_variants table
    op.create_table(
        'product_variants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), unique=True),
        sa.Column('price', sa.Numeric(10, 2)),
        sa.Column('stock_quantity', sa.Integer()),
        sa.Column('attributes', sa.JSON()),
        sa.Column('image_url', sa.String(500)),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_product_variants_product_id', 'product_variants', ['product_id'])

    # Create affiliate_approvals table
    op.create_table(
        'affiliate_approvals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='affiliateapprovalstatusdb'), server_default='pending'),
        sa.Column('application_message', sa.Text()),
        sa.Column('application_data', sa.JSON()),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('reviewed_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('rejection_reason', sa.Text()),
        sa.Column('applied_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('influencer_id', 'product_id', name='uq_influencer_product')
    )
    op.create_index('ix_affiliate_approvals_influencer_id', 'affiliate_approvals', ['influencer_id'])
    op.create_index('ix_affiliate_approvals_product_id', 'affiliate_approvals', ['product_id'])
    op.create_index('ix_affiliate_approvals_status', 'affiliate_approvals', ['status'])

    # Create affiliate_links table
    op.create_table(
        'affiliate_links',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('affiliate_code', sa.String(50), nullable=False, unique=True),
        sa.Column('link_url', sa.Text(), nullable=False),
        sa.Column('short_url', sa.String(255)),
        sa.Column('qr_code_url', sa.String(500)),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('orders', sa.Integer(), server_default='0'),
        sa.Column('total_sales_amount', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('total_commission_earned', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_clicked_at', sa.DateTime())
    )
    op.create_index('ix_affiliate_links_affiliate_code', 'affiliate_links', ['affiliate_code'])
    op.create_index('ix_affiliate_links_influencer_id', 'affiliate_links', ['influencer_id'])
    op.create_index('ix_affiliate_links_product_id', 'affiliate_links', ['product_id'])

    # Create affiliate_clicks table
    op.create_table(
        'affiliate_clicks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('affiliate_link_id', sa.String(36), sa.ForeignKey('affiliate_links.id', ondelete='CASCADE'), nullable=False),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('referrer', sa.Text()),
        sa.Column('country', sa.String(2)),
        sa.Column('device_type', sa.String(20)),
        sa.Column('converted', sa.Boolean(), server_default='false'),
        sa.Column('order_id', sa.String(36), nullable=True),
        sa.Column('clicked_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_affiliate_clicks_affiliate_link_id', 'affiliate_clicks', ['affiliate_link_id'])
    op.create_index('ix_affiliate_clicks_clicked_at', 'affiliate_clicks', ['clicked_at'])

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_number', sa.String(50), nullable=False, unique=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_id', sa.String(36), sa.ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('brand_profile_id', sa.String(36), sa.ForeignKey('brand_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attributed_influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('affiliate_code', sa.String(50)),
        sa.Column('affiliate_link_id', sa.String(36), sa.ForeignKey('affiliate_links.id', ondelete='SET NULL'), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_notes', sa.Text()),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), server_default='KES'),
        sa.Column('commission_type', sa.String(20)),
        sa.Column('commission_rate', sa.Numeric(5, 2)),
        sa.Column('commission_amount', sa.Numeric(10, 2)),
        sa.Column('platform_fee_type', sa.String(20)),
        sa.Column('platform_fee_rate', sa.Numeric(5, 2)),
        sa.Column('platform_fee_amount', sa.Numeric(10, 2)),
        sa.Column('net_commission', sa.Numeric(10, 2)),
        sa.Column('brand_receives', sa.Numeric(10, 2)),
        sa.Column('status', sa.Enum('pending', 'contacted', 'in_progress', 'fulfilled', 'cancelled', name='orderstatusdb'), server_default='pending'),
        sa.Column('brand_notes', sa.Text()),
        sa.Column('cancellation_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('contacted_at', sa.DateTime()),
        sa.Column('fulfilled_at', sa.DateTime()),
        sa.Column('cancelled_at', sa.DateTime())
    )
    op.create_index('ix_orders_order_number', 'orders', ['order_number'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_brand_profile_id', 'orders', ['brand_profile_id'])
    op.create_index('ix_orders_attributed_influencer_id', 'orders', ['attributed_influencer_id'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])

    # Add FK constraint for order_id in affiliate_clicks (circular dependency)
    op.create_foreign_key(
        'fk_affiliate_clicks_order_id',
        'affiliate_clicks',
        'orders',
        ['order_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create affiliate_commissions table
    op.create_table(
        'affiliate_commissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('gross_commission', sa.Numeric(10, 2), nullable=False),
        sa.Column('platform_fee', sa.Numeric(10, 2), nullable=False),
        sa.Column('net_commission', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'paid', 'cancelled', name='commissionstatusdb'), server_default='pending'),
        sa.Column('wallet_transaction_id', sa.String(36), sa.ForeignKey('wallet_transactions.id'), nullable=True),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('commission_type', sa.String(20)),
        sa.Column('commission_rate', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('ix_affiliate_commissions_order_id', 'affiliate_commissions', ['order_id'])
    op.create_index('ix_affiliate_commissions_influencer_id', 'affiliate_commissions', ['influencer_id'])
    op.create_index('ix_affiliate_commissions_status', 'affiliate_commissions', ['status'])

    # Create affiliate_analytics table
    op.create_table(
        'affiliate_analytics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('influencer_id', sa.String(36), sa.ForeignKey('influencer_profiles.id', ondelete='CASCADE'), nullable=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True),
        sa.Column('brand_profile_id', sa.String(36), sa.ForeignKey('brand_profiles.id', ondelete='CASCADE'), nullable=True),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('orders', sa.Integer(), server_default='0'),
        sa.Column('orders_fulfilled', sa.Integer(), server_default='0'),
        sa.Column('orders_cancelled', sa.Integer(), server_default='0'),
        sa.Column('total_sales', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('total_commissions', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('total_platform_fees', sa.Numeric(12, 2), server_default='0.00'),
        sa.Column('conversion_rate', sa.Numeric(5, 2)),
        sa.Column('average_order_value', sa.Numeric(10, 2)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_affiliate_analytics_date', 'affiliate_analytics', ['date'])
    op.create_index('ix_affiliate_analytics_influencer_id', 'affiliate_analytics', ['influencer_id'])
    op.create_index('ix_affiliate_analytics_product_id', 'affiliate_analytics', ['product_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('affiliate_analytics')
    op.drop_table('affiliate_commissions')
    op.drop_table('orders')
    op.drop_table('affiliate_clicks')
    op.drop_table('affiliate_links')
    op.drop_table('affiliate_approvals')
    op.drop_table('product_variants')
    op.drop_table('products')
    op.drop_table('brand_profiles')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS platformfeetypedb')
    op.execute('DROP TYPE IF EXISTS preferredcontactmethoddb')
    op.execute('DROP TYPE IF EXISTS commissionstatusdb')
    op.execute('DROP TYPE IF EXISTS orderstatusdb')
    op.execute('DROP TYPE IF EXISTS affiliateapprovalstatusdb')
    op.execute('DROP TYPE IF EXISTS productstatusdb')
    op.execute('DROP TYPE IF EXISTS commissiontypedb')

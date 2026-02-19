"""add payment_reference to orders table

Revision ID: add_payment_reference
Revises: add_digital_product_fields
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_payment_reference'
down_revision = 'brand_profile_per_brand'
branch_labels = None
depends_on = None


def upgrade():
    # Add payment_reference column to orders table
    op.add_column('orders', sa.Column('payment_reference', sa.String(100), nullable=True))
    op.create_index('ix_orders_payment_reference', 'orders', ['payment_reference'], unique=True)


def downgrade():
    op.drop_index('ix_orders_payment_reference', table_name='orders')
    op.drop_column('orders', 'payment_reference')

"""add digital product fields to products and orders tables

Revision ID: add_digital_product_fields
Revises: add_affiliate_commerce_tables
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_digital_product_fields'
down_revision = 'affiliate_commerce_001'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------ #
    # products table – digital product columns
    # ------------------------------------------------------------------ #
    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('is_digital', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('digital_file_key', sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column('digital_file_name', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('digital_file_size', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('digital_file_type', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('digital_preview_url', sa.String(500), nullable=True))

    # ------------------------------------------------------------------ #
    # orders table – digital download tracking
    # ------------------------------------------------------------------ #
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('digital_download_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('digital_download_count')

    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('digital_preview_url')
        batch_op.drop_column('digital_file_type')
        batch_op.drop_column('digital_file_size')
        batch_op.drop_column('digital_file_name')
        batch_op.drop_column('digital_file_key')
        batch_op.drop_column('is_digital')

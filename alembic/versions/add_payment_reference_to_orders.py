"""add payment_reference to orders table

Revision ID: add_payment_reference
Revises: add_digital_product_fields
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_payment_reference'
down_revision = 'add_digital_product_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add payment_reference column to orders table
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('payment_reference', sa.String(100), nullable=True))
        batch_op.create_index('ix_orders_payment_reference', ['payment_reference'], unique=True)


def downgrade():
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_index('ix_orders_payment_reference')
        batch_op.drop_column('payment_reference')

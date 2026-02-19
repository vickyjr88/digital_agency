"""brand_profile_per_brand: one profile per Brand instead of per User

Revision ID: brand_profile_per_brand
Revises: add_digital_product_fields
Create Date: 2026-02-19

Changes:
  - brand_profiles.brand_id: nullable=True  → nullable=False, unique=True
  - brand_profiles.user_id:  unique=True    → unique=False  (non-unique FK)

Any existing rows that have NULL brand_id are deleted first (they cannot be
migrated without knowing which brand they belong to).
"""
from alembic import op
import sqlalchemy as sa

revision = 'brand_profile_per_brand'
down_revision = 'add_digital_product_fields'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop rows without a brand_id so NOT NULL constraint is safe to add
    op.execute("DELETE FROM brand_profiles WHERE brand_id IS NULL")

    with op.batch_alter_table('brand_profiles') as batch_op:
        # 2. Drop old unique constraint on user_id
        batch_op.drop_constraint('brand_profiles_user_id_key', type_='unique')

        # 3. Make brand_id NOT NULL and unique
        batch_op.alter_column('brand_id', nullable=False)
        batch_op.create_unique_constraint('uq_brand_profiles_brand_id', ['brand_id'])


def downgrade():
    with op.batch_alter_table('brand_profiles') as batch_op:
        batch_op.drop_constraint('uq_brand_profiles_brand_id', type_='unique')
        batch_op.alter_column('brand_id', nullable=True)
        batch_op.create_unique_constraint('brand_profiles_user_id_key', ['user_id'])

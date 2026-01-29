"""Fix campaign status enum and nullable columns

Revision ID: fix_campaign_status_enum
Revises: add_marketplace_tables_001
Create Date: 2026-01-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_campaign_status_enum'
down_revision = 'add_marketplace_tables_001'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Fix Enums (both potential names)
    enums_to_fix = ['campaignstatusdb', 'campaignstatus']
    for enum_name in enums_to_fix:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = '{enum_name}' AND e.enumlabel = 'open') THEN
                        ALTER TYPE {enum_name} ADD VALUE 'open';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = '{enum_name}' AND e.enumlabel = 'OPEN') THEN
                        ALTER TYPE {enum_name} ADD VALUE 'OPEN';
                    END IF;
                END IF;
            END$$;
        """)

    # 2. Fix Column Nullability for Open Campaigns
    with op.batch_alter_table('campaigns') as batch_op:
        batch_op.alter_column('influencer_id', existing_type=sa.String(36), nullable=True)
        batch_op.alter_column('package_id', existing_type=sa.String(36), nullable=True)

def downgrade():
    pass

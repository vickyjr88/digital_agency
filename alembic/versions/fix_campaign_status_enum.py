"""Fix campaign status enum

Revision ID: fix_campaign_status_enum
Revises: add_marketplace_tables_001
Create Date: 2026-01-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'fix_campaign_status_enum'
down_revision = 'add_marketplace_tables_001'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL specific: update the enum type to include 'open' (lowercase) if missing
    # Note: ALTER TYPE ... ADD VALUE cannot be executed inside a transaction block in some versions
    # But Alembic runs inside one by default. 
    # To run outside transaction, we can use "commit" but alembic API is tied to connection.
    # However, since we are likely on Postgres 12+, we can try.
    # Or just use raw SQL with "commit" if needed.
    
    # We use a raw SQL block with a DO block to safely check and add
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'campaignstatusdb' AND e.enumlabel = 'open') THEN
                ALTER TYPE campaignstatusdb ADD VALUE 'open';
            END IF;
        END$$;
    """)

def downgrade():
    # Cannot remove values from Enums in Postgres easily
    pass

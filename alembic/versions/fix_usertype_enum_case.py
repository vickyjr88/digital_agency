"""Fix usertype enum case mismatch

Revision ID: fix_usertype_enum_case
Revises: add_missing_social_columns
Create Date: 2024-02-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_usertype_enum_case'
down_revision = 'add_missing_social_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection
    conn = op.get_bind()

    # First, check if the lowercase values already exist in the enum
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'brand'
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'usertype')
        );
    """)).scalar()

    if not result:
        # Add lowercase enum values
        conn.execute(sa.text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'brand'"))
        conn.execute(sa.text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'influencer'"))
        conn.execute(sa.text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'admin'"))

        # Update all existing data to use lowercase values
        conn.execute(sa.text("UPDATE users SET user_type = 'brand' WHERE user_type = 'BRAND'"))
        conn.execute(sa.text("UPDATE users SET user_type = 'influencer' WHERE user_type = 'INFLUENCER'"))
        conn.execute(sa.text("UPDATE users SET user_type = 'admin' WHERE user_type = 'ADMIN'"))

        print("✓ Added lowercase enum values and updated existing data")
    else:
        print("✓ Lowercase enum values already exist")


def downgrade():
    # Get connection
    conn = op.get_bind()

    # Update data back to uppercase
    conn.execute(sa.text("UPDATE users SET user_type = 'BRAND' WHERE user_type = 'brand'"))
    conn.execute(sa.text("UPDATE users SET user_type = 'INFLUENCER' WHERE user_type = 'influencer'"))
    conn.execute(sa.text("UPDATE users SET user_type = 'ADMIN' WHERE user_type = 'admin'"))

    # Note: PostgreSQL doesn't support removing enum values easily
    # You would need to recreate the enum type to remove values
    print("✓ Reverted data to uppercase values")

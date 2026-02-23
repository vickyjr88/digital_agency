"""Convert enum columns to varchar

Revision ID: convert_enums_to_varchar
Revises: fix_usertype_enum_case
Create Date: 2024-02-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'convert_enums_to_varchar'
down_revision = 'fix_usertype_enum_case'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection
    conn = op.get_bind()

    # Convert users table enum columns to varchar
    print("Converting users.role from userrole enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE users
        ALTER COLUMN role TYPE varchar(20)
        USING role::text
    """))

    print("Converting users.user_type from usertype enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE users
        ALTER COLUMN user_type TYPE varchar(20)
        USING user_type::text
    """))

    print("Converting users.subscription_tier from subscriptiontier enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE users
        ALTER COLUMN subscription_tier TYPE varchar(20)
        USING subscription_tier::text
    """))

    print("Converting users.subscription_status from subscriptionstatus enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE users
        ALTER COLUMN subscription_status TYPE varchar(20)
        USING subscription_status::text
    """))

    # Convert content table
    print("Converting content.status from contentstatus enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE content
        ALTER COLUMN status TYPE varchar(20)
        USING status::text
    """))

    # Convert team_members table
    print("Converting team_members.role from teamrole enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE team_members
        ALTER COLUMN role TYPE varchar(20)
        USING role::text
    """))

    # Convert transactions table
    print("Converting transactions.status from paymentstatus enum to varchar(20)...")
    conn.execute(sa.text("""
        ALTER TABLE transactions
        ALTER COLUMN status TYPE varchar(20)
        USING status::text
    """))

    print("✓ All enum columns converted to varchar!")


def downgrade():
    # Get connection
    conn = op.get_bind()

    # Note: This is complex because we need to recreate the enum types
    # For now, just print a warning
    print("⚠️ Downgrade not implemented - enum types would need to be recreated")
    print("⚠️ Data will remain as varchar(20)")

"""Fix all enum types - convert to varchar and update values to lowercase

Revision ID: 2026_03_09_0000_fix_all_enum_types
Revises: 2026_02_23_1623-c76d836672f6_add_tumanasi_tables
Create Date: 2026-03-09 00:00:00.000000

This migration:
1. Converts all PostgreSQL native enum types to VARCHAR(20)
2. Updates all existing UPPERCASE values to lowercase
3. Ensures consistency between database schema and Python code
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_09_0000_fix_all_enum_types'
down_revision = '2026_02_23_1623-c76d836672f6_add_tumanasi_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Convert enum types to varchar and normalize values to lowercase"""
    conn = op.get_bind()

    print("\n" + "=" * 80)
    print("STARTING ENUM TYPE MIGRATION")
    print("=" * 80)

    # ========================================================================
    # STEP 1: Convert users.role (userrole -> varchar)
    # ========================================================================
    print("\n[1/8] Converting users.role from userrole enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE users
            ALTER COLUMN role TYPE varchar(20)
            USING role::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE users
        SET role = lower(role)
        WHERE role != lower(role)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 2: Convert users.user_type (usertype -> varchar)
    # ========================================================================
    print("\n[2/8] Converting users.user_type from usertype enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE users
            ALTER COLUMN user_type TYPE varchar(20)
            USING user_type::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE users
        SET user_type = lower(user_type)
        WHERE user_type != lower(user_type)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 3: Convert users.subscription_tier
    # ========================================================================
    print("\n[3/8] Converting users.subscription_tier from subscriptiontier enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE users
            ALTER COLUMN subscription_tier TYPE varchar(20)
            USING subscription_tier::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE users
        SET subscription_tier = lower(subscription_tier)
        WHERE subscription_tier != lower(subscription_tier)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 4: Convert users.subscription_status
    # ========================================================================
    print("\n[4/8] Converting users.subscription_status from subscriptionstatus enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE users
            ALTER COLUMN subscription_status TYPE varchar(20)
            USING subscription_status::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE users
        SET subscription_status = lower(subscription_status)
        WHERE subscription_status != lower(subscription_status)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 5: Convert content.status
    # ========================================================================
    print("\n[5/8] Converting content.status from contentstatus enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE content
            ALTER COLUMN status TYPE varchar(20)
            USING status::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE content
        SET status = lower(status)
        WHERE status != lower(status)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 6: Convert team_members.role
    # ========================================================================
    print("\n[6/8] Converting team_members.role from teamrole enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE team_members
            ALTER COLUMN role TYPE varchar(20)
            USING role::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE team_members
        SET role = lower(role)
        WHERE role != lower(role)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 7: Convert transactions.status
    # ========================================================================
    print("\n[7/8] Converting transactions.status from paymentstatus enum to varchar(20)...")
    try:
        conn.execute(sa.text("""
            ALTER TABLE transactions
            ALTER COLUMN status TYPE varchar(20)
            USING status::text
        """))
        print("  ✓ Column type converted to varchar(20)")
    except Exception as e:
        if "already" in str(e).lower() or "varchar" in str(e).lower():
            print("  ⚠ Column already varchar, skipping conversion")
        else:
            raise

    # Update values to lowercase
    print("  Updating values to lowercase...")
    result = conn.execute(sa.text("""
        UPDATE transactions
        SET status = lower(status)
        WHERE status != lower(status)
    """))
    print(f"  ✓ Updated {result.rowcount} rows")

    # ========================================================================
    # STEP 8: Verify all conversions
    # ========================================================================
    print("\n[8/8] Verifying all enum columns are now varchar...")

    # Check users table
    result = conn.execute(sa.text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name IN ('role', 'user_type', 'subscription_tier', 'subscription_status')
        ORDER BY column_name
    """))

    print("\n  Users table columns:")
    for row in result:
        print(f"    {row.column_name}: {row.data_type}")

    print("\n" + "=" * 80)
    print("✓ ENUM TYPE MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nAll enum types have been converted to varchar(20)")
    print("All values have been normalized to lowercase")
    print("\nYou can now restart your application.")
    print("=" * 80 + "\n")


def downgrade():
    """Revert varchar columns back to uppercase values (enum types won't be recreated)"""
    conn = op.get_bind()

    print("\n⚠️  WARNING: This downgrade will NOT recreate enum types")
    print("It will only convert values back to UPPERCASE\n")

    # Revert users.role
    conn.execute(sa.text("UPDATE users SET role = upper(role) WHERE role = lower(role)"))

    # Revert users.user_type
    conn.execute(sa.text("UPDATE users SET user_type = upper(user_type) WHERE user_type = lower(user_type)"))

    # Revert users.subscription_tier
    conn.execute(sa.text("UPDATE users SET subscription_tier = upper(subscription_tier) WHERE subscription_tier = lower(subscription_tier)"))

    # Revert users.subscription_status
    conn.execute(sa.text("UPDATE users SET subscription_status = upper(subscription_status) WHERE subscription_status = lower(subscription_status)"))

    # Revert content.status
    conn.execute(sa.text("UPDATE content SET status = upper(status) WHERE status = lower(status)"))

    # Revert team_members.role
    conn.execute(sa.text("UPDATE team_members SET role = upper(role) WHERE role = lower(role)"))

    # Revert transactions.status
    conn.execute(sa.text("UPDATE transactions SET status = upper(status) WHERE status = lower(status)"))

    print("✓ Values reverted to UPPERCASE")
    print("⚠️  Column types remain as varchar(20)")

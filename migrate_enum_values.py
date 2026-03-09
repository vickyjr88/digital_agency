#!/usr/bin/env python3
"""
Migration Script: Convert UserRole and UserType enum values to lowercase
Purpose: Update existing database records to match new lowercase enum definitions
Date: 2024-02-24
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment variables"""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USERNAME", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_DATABASE", "dexter_db")

    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def verify_before_migration(session):
    """Check current state of data before migration"""
    print("\n📊 Current Data State (Before Migration):")
    print("=" * 60)

    # Check UserRole values
    result = session.execute(text("""
        SELECT role, COUNT(*) as count
        FROM users
        GROUP BY role
        ORDER BY count DESC
    """))
    print("\nUserRole distribution:")
    for row in result:
        print(f"  {row.role}: {row.count} users")

    # Check UserType values
    result = session.execute(text("""
        SELECT user_type, COUNT(*) as count
        FROM users
        GROUP BY user_type
        ORDER BY count DESC
    """))
    print("\nUserType distribution:")
    for row in result:
        print(f"  {row.user_type}: {row.count} users")

    print("=" * 60)

def migrate_enum_values(session):
    """Migrate enum values from UPPERCASE to lowercase"""
    print("\n🔄 Starting Migration...")
    print("=" * 60)

    # Backup recommendation
    print("\n⚠️  IMPORTANT: Make sure you have a database backup before proceeding!")
    print("   To create a backup, run:")
    print("   docker exec dexter-postgres pg_dump -U postgres dexter_db > backup_$(date +%Y%m%d_%H%M%S).sql")

    response = input("\nDo you want to proceed with the migration? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled.")
        return False

    try:
        # Migrate UserRole values
        print("\n1️⃣ Migrating UserRole values...")

        # ADMIN -> admin
        result = session.execute(text("""
            UPDATE users
            SET role = 'admin'
            WHERE role = 'ADMIN'
        """))
        admin_count = result.rowcount
        print(f"   ✅ Updated {admin_count} records: ADMIN -> admin")

        # USER -> user
        result = session.execute(text("""
            UPDATE users
            SET role = 'user'
            WHERE role = 'USER'
        """))
        user_count = result.rowcount
        print(f"   ✅ Updated {user_count} records: USER -> user")

        # Migrate UserType values
        print("\n2️⃣ Migrating UserType values...")

        # BRAND -> brand
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'brand'
            WHERE user_type = 'BRAND'
        """))
        brand_count = result.rowcount
        print(f"   ✅ Updated {brand_count} records: BRAND -> brand")

        # INFLUENCER -> influencer
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'influencer'
            WHERE user_type = 'INFLUENCER'
        """))
        influencer_count = result.rowcount
        print(f"   ✅ Updated {influencer_count} records: INFLUENCER -> influencer")

        # ADMIN -> admin (for user_type)
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'admin'
            WHERE user_type = 'ADMIN'
        """))
        admin_type_count = result.rowcount
        print(f"   ✅ Updated {admin_type_count} records: ADMIN -> admin (user_type)")

        # Commit the changes
        session.commit()

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print(f"\nTotal records updated:")
        print(f"  UserRole: {admin_count + user_count}")
        print(f"  UserType: {brand_count + influencer_count + admin_type_count}")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        session.rollback()
        return False

def verify_after_migration(session):
    """Verify data state after migration"""
    print("\n📊 Data State After Migration:")
    print("=" * 60)

    # Check UserRole values
    result = session.execute(text("""
        SELECT role, COUNT(*) as count
        FROM users
        GROUP BY role
        ORDER BY count DESC
    """))
    print("\nUserRole distribution:")
    all_lowercase = True
    for row in result:
        is_lowercase = row.role.islower() if row.role else True
        status = "✅" if is_lowercase else "❌"
        print(f"  {status} {row.role}: {row.count} users")
        if not is_lowercase:
            all_lowercase = False

    # Check UserType values
    result = session.execute(text("""
        SELECT user_type, COUNT(*) as count
        FROM users
        GROUP BY user_type
        ORDER BY count DESC
    """))
    print("\nUserType distribution:")
    for row in result:
        is_lowercase = row.user_type.islower() if row.user_type else True
        status = "✅" if is_lowercase else "❌"
        print(f"  {status} {row.user_type}: {row.count} users")
        if not is_lowercase:
            all_lowercase = False

    print("=" * 60)

    if all_lowercase:
        print("\n✅ All enum values are now lowercase!")
    else:
        print("\n⚠️  Warning: Some uppercase values remain. Check the data above.")

def main():
    print("🚀 Enum Values Migration Script")
    print("=" * 60)
    print("This script will convert UserRole and UserType enum values")
    print("from UPPERCASE to lowercase in the database.")
    print("=" * 60)

    # Get database URL
    db_url = get_database_url()
    print(f"\n🔌 Connecting to database...")

    try:
        # Create engine and session
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        print("✅ Database connection successful!")

        # Verify current state
        verify_before_migration(session)

        # Run migration
        success = migrate_enum_values(session)

        if success:
            # Verify after migration
            verify_after_migration(session)

        session.close()

        if success:
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Deploy the updated code with lowercase enum definitions")
            print("2. Test the application to ensure everything works")
            print("3. Monitor logs for any enum-related errors")
            return 0
        else:
            print("\n❌ Migration failed. Please check the errors above.")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

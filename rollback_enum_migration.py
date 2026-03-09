#!/usr/bin/env python3
"""
Rollback Script: Revert UserRole and UserType enum values to UPPERCASE
Purpose: Rollback the enum migration if issues occur
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

def rollback_enum_values(session):
    """Rollback enum values from lowercase to UPPERCASE"""
    print("\n🔄 Starting Rollback...")
    print("=" * 60)

    print("\n⚠️  WARNING: This will revert all enum values to UPPERCASE!")
    print("   Make sure your code expects UPPERCASE enum values.")

    response = input("\nDo you want to proceed with the rollback? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Rollback cancelled.")
        return False

    try:
        # Rollback UserRole values
        print("\n1️⃣ Rolling back UserRole values...")

        # admin -> ADMIN
        result = session.execute(text("""
            UPDATE users
            SET role = 'ADMIN'
            WHERE role = 'admin'
        """))
        admin_count = result.rowcount
        print(f"   ✅ Reverted {admin_count} records: admin -> ADMIN")

        # user -> USER
        result = session.execute(text("""
            UPDATE users
            SET role = 'USER'
            WHERE role = 'user'
        """))
        user_count = result.rowcount
        print(f"   ✅ Reverted {user_count} records: user -> USER")

        # Rollback UserType values
        print("\n2️⃣ Rolling back UserType values...")

        # brand -> BRAND
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'BRAND'
            WHERE user_type = 'brand'
        """))
        brand_count = result.rowcount
        print(f"   ✅ Reverted {brand_count} records: brand -> BRAND")

        # influencer -> INFLUENCER
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'INFLUENCER'
            WHERE user_type = 'influencer'
        """))
        influencer_count = result.rowcount
        print(f"   ✅ Reverted {influencer_count} records: influencer -> INFLUENCER")

        # admin -> ADMIN (for user_type)
        result = session.execute(text("""
            UPDATE users
            SET user_type = 'ADMIN'
            WHERE user_type = 'admin'
        """))
        admin_type_count = result.rowcount
        print(f"   ✅ Reverted {admin_type_count} records: admin -> ADMIN (user_type)")

        # Commit the changes
        session.commit()

        print("\n" + "=" * 60)
        print("✅ Rollback completed successfully!")
        print(f"\nTotal records reverted:")
        print(f"  UserRole: {admin_count + user_count}")
        print(f"  UserType: {brand_count + influencer_count + admin_type_count}")

        return True

    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        session.rollback()
        return False

def verify_after_rollback(session):
    """Verify data state after rollback"""
    print("\n📊 Data State After Rollback:")
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

def main():
    print("⏪ Enum Values Rollback Script")
    print("=" * 60)
    print("This script will revert UserRole and UserType enum values")
    print("from lowercase back to UPPERCASE in the database.")
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

        # Run rollback
        success = rollback_enum_values(session)

        if success:
            # Verify after rollback
            verify_after_rollback(session)

        session.close()

        if success:
            print("\n✅ Rollback completed successfully!")
            print("\nNext steps:")
            print("1. Deploy code with UPPERCASE enum definitions if needed")
            print("2. Test the application")
            return 0
        else:
            print("\n❌ Rollback failed. Please check the errors above.")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Verification Script: Check current state of UserRole and UserType enum values
Purpose: Verify enum values in the database without making changes
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

def verify_enum_values(session):
    """Check current state of enum values"""
    print("\n📊 Current Enum Values State")
    print("=" * 60)

    # Total users
    result = session.execute(text("SELECT COUNT(*) as total FROM users"))
    total_users = result.scalar()
    print(f"\n👥 Total Users: {total_users}")

    # Check UserRole values
    print("\n🔐 UserRole Distribution:")
    print("-" * 60)
    result = session.execute(text("""
        SELECT role, COUNT(*) as count
        FROM users
        GROUP BY role
        ORDER BY count DESC
    """))

    has_uppercase_role = False
    has_lowercase_role = False

    for row in result:
        is_lowercase = row.role and row.role.islower()
        is_uppercase = row.role and row.role.isupper()

        if is_uppercase:
            has_uppercase_role = True
            status = "⚠️  UPPERCASE"
        elif is_lowercase:
            has_lowercase_role = True
            status = "✅ lowercase"
        else:
            status = "❓ mixed/unknown"

        percentage = (row.count / total_users * 100) if total_users > 0 else 0
        print(f"  {status:20} {row.role:15} {row.count:6} users ({percentage:5.1f}%)")

    # Check UserType values
    print("\n👤 UserType Distribution:")
    print("-" * 60)
    result = session.execute(text("""
        SELECT user_type, COUNT(*) as count
        FROM users
        GROUP BY user_type
        ORDER BY count DESC
    """))

    has_uppercase_type = False
    has_lowercase_type = False

    for row in result:
        is_lowercase = row.user_type and row.user_type.islower()
        is_uppercase = row.user_type and row.user_type.isupper()

        if is_uppercase:
            has_uppercase_type = True
            status = "⚠️  UPPERCASE"
        elif is_lowercase:
            has_lowercase_type = True
            status = "✅ lowercase"
        else:
            status = "❓ mixed/unknown"

        percentage = (row.count / total_users * 100) if total_users > 0 else 0
        print(f"  {status:20} {row.user_type:15} {row.count:6} users ({percentage:5.1f}%)")

    print("=" * 60)

    # Summary and recommendations
    print("\n📋 Summary:")

    if has_uppercase_role or has_uppercase_type:
        print("\n⚠️  UPPERCASE enum values detected!")
        print("   Your code expects: lowercase values")
        print("   Action required: Run migration script")
        print("   Command: python migrate_enum_values.py")
        return False
    elif has_lowercase_role and has_lowercase_type:
        print("\n✅ All enum values are lowercase!")
        print("   Your code expects: lowercase values")
        print("   Status: Database and code are in sync ✓")
        return True
    else:
        print("\n❓ Unknown or mixed state detected")
        print("   Please review the data above")
        return False

def show_sample_data(session):
    """Show sample user data for verification"""
    print("\n📝 Sample User Data (First 5 Users):")
    print("=" * 60)

    result = session.execute(text("""
        SELECT id, email, role, user_type, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 5
    """))

    print(f"{'Email':<30} {'Role':<10} {'Type':<12} {'Created':<20}")
    print("-" * 60)
    for row in result:
        created = row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "N/A"
        print(f"{row.email:<30} {row.role:<10} {row.user_type:<12} {created:<20}")

    print("=" * 60)

def main():
    print("🔍 Enum Values Verification Script")
    print("=" * 60)
    print("This script checks the current state of UserRole and UserType")
    print("enum values in the database without making any changes.")
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

        # Verify enum values
        is_consistent = verify_enum_values(session)

        # Show sample data
        show_sample_data(session)

        session.close()

        if is_consistent:
            print("\n✅ Verification complete: Database is consistent with code!")
            return 0
        else:
            print("\n⚠️  Verification complete: Migration may be needed!")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

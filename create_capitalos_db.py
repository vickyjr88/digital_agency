#!/usr/bin/env python3
"""
Create capitalos database in Neon PostgreSQL
Run this script to create a new database called 'capitalos'
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create capitalos database"""

    # Get the database URL from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    print(f"📊 Connecting to database...")

    try:
        # Connect to the default database (neondb)
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database already exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'capitalos'"
        )

        if cursor.fetchone():
            print("✅ Database 'capitalos' already exists!")
            cursor.close()
            conn.close()
            return True

        # Create the database
        print("🔨 Creating database 'capitalos'...")
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier('capitalos')
            )
        )

        print("✅ Database 'capitalos' created successfully!")

        # Display the new connection string
        base_url = database_url.rsplit('/', 1)[0]
        new_database_url = f"{base_url}/capitalos?sslmode=require"

        print("\n" + "="*60)
        print("📝 New Database Connection String:")
        print("="*60)
        print(new_database_url)
        print("="*60)
        print("\n💡 Add this to your .env file:")
        print(f"CAPITALOS_DATABASE_URL={new_database_url}")
        print("="*60)

        cursor.close()
        conn.close()

        return True

    except psycopg2.errors.InsufficientPrivilege as e:
        print("\n❌ Insufficient privileges to create database")
        print("💡 You need to create the database through Neon Console:")
        print("   1. Go to https://console.neon.tech")
        print("   2. Select your project")
        print("   3. Click 'Databases' → 'New Database'")
        print("   4. Name it 'capitalos'")
        return False

    except Exception as e:
        print(f"\n❌ Error creating database: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Creating 'capitalos' Database")
    print("="*60 + "\n")

    success = create_database()

    if success:
        print("\n✅ Done! Database is ready to use.")
    else:
        print("\n❌ Failed to create database. Please create it manually through Neon Console.")

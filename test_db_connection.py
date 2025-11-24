# Database Connection Test Script

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/dexter")

print(f"Testing connection to: {DATABASE_URL}")
print("-" * 60)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {version}")
        
        # Check if database exists
        result = conn.execute(text("SELECT current_database();"))
        db_name = result.fetchone()[0]
        print(f"Connected to database: {db_name}")
        
        # List tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        
        if tables:
            print(f"\nExisting tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nNo tables found (database is empty)")
        
        print("\n✅ All checks passed!")
        sys.exit(0)
        
except Exception as e:
    print(f"❌ Connection failed!")
    print(f"Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check if PostgreSQL container is running: docker ps | grep dexter-db")
    print("2. Check DATABASE_URL in .env file")
    print("3. Verify network connectivity: docker network ls")
    sys.exit(1)

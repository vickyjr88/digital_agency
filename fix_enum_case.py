"""
Fix UserType enum case to use uppercase values
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    exit(1)

print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if uppercase values exist in the enum
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'BRAND'
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'usertype')
        );
    """))
    uppercase_exists = result.scalar()

    if not uppercase_exists:
        print("Adding uppercase enum values...")
        conn.execute(text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'BRAND'"))
        conn.execute(text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'INFLUENCER'"))
        conn.execute(text("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'ADMIN'"))
        conn.commit()
        print("✅ Added uppercase enum values")
    else:
        print("✅ Uppercase enum values already exist")

    # Update all existing data to use uppercase values
    print("Updating existing records to uppercase...")
    result = conn.execute(text("UPDATE users SET user_type = 'BRAND' WHERE user_type = 'brand'"))
    print(f"  Updated {result.rowcount} brand users")
    
    result = conn.execute(text("UPDATE users SET user_type = 'INFLUENCER' WHERE user_type = 'influencer'"))
    print(f"  Updated {result.rowcount} influencer users")
    
    result = conn.execute(text("UPDATE users SET user_type = 'ADMIN' WHERE user_type = 'admin'"))
    print(f"  Updated {result.rowcount} admin users")
    
    conn.commit()
    print("✅ All records updated successfully!")

print("\n🎉 Enum case fix completed!")

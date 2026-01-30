
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment!")
    exit(1)

# Fix for Heroku/Railway style URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with autocommit for enum alterations
engine = create_engine(DATABASE_URL)

def apply_migration():
    print(f"🚀 Connecting to database: {DATABASE_URL.split('@')[-1]}")
    
    # 1. Add columns to deliverables
    with engine.begin() as conn:
        print("🔍 Checking 'deliverables' columns...")
        
        # bid_id
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='deliverables' AND column_name='bid_id';")).fetchone()
        if not res:
            print("➕ Adding 'bid_id' to 'deliverables'...")
            conn.execute(text("ALTER TABLE deliverables ADD COLUMN bid_id VARCHAR(36);"))
        
        # influencer_id
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='deliverables' AND column_name='influencer_id';")).fetchone()
        if not res:
            print("➕ Adding 'influencer_id' to 'deliverables'...")
            conn.execute(text("ALTER TABLE deliverables ADD COLUMN influencer_id VARCHAR(36);"))
            
        print("✅ Column checks complete.")

    # 2. Update Enums
    # Postgres ADD VALUE cannot be run inside a transaction block
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("🔍 Updating 'bidstatusdb' enum...")
        for value in ['completed', 'paid']:
            try:
                # This works for Postgres 12+
                conn.execute(text(f"ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS '{value}';"))
                print(f"✅ Ensured '{value}' exists in 'bidstatusdb'")
            except Exception as e:
                # Fallback for older Postgres or if it's not a native enum
                if 'already exists' in str(e).lower():
                    print(f"ℹ️ Value '{value}' already exists.")
                else:
                    print(f"⚠️ Warning adding '{value}' to enum: {e}")

    print("✅ All marketplace refactor migrations applied.")

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

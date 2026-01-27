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

engine = create_engine(DATABASE_URL)

def apply_migration():
    print(f"🚀 Connecting to database: {DATABASE_URL.split('@')[-1]}")
    
    with engine.connect() as conn:
        # 1. Check/Add scheduled_at to content
        print("🔍 Checking 'content.scheduled_at'...")
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='content' AND column_name='scheduled_at';")).fetchone()
        if not res:
            print("➕ Adding 'scheduled_at' to 'content'...")
            conn.execute(text("ALTER TABLE content ADD COLUMN scheduled_at TIMESTAMP;"))
        
        # 2. Check/Add meta_data to content
        print("🔍 Checking 'content.meta_data'...")
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='content' AND column_name='meta_data';")).fetchone()
        if not res:
            print("➕ Adding 'meta_data' to 'content'...")
            conn.execute(text("ALTER TABLE content ADD COLUMN meta_data JSONB;"))

        # 3. Check/Add content_generated_count to usage
        print("🔍 Checking 'usage.content_generated_count'...")
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='usage' AND column_name='content_generated_count';")).fetchone()
        if not res:
            print("➕ Adding 'content_generated_count' to 'usage'...")
            conn.execute(text("ALTER TABLE usage ADD COLUMN content_generated_count INTEGER DEFAULT 0;"))
            
        conn.commit()
    print("✅ All migrations applied.")

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

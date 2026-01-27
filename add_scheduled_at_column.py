import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    exit(1)

# Ensure it uses postgresql:// instead of postgres:// if needed (Heroku/Railway style)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def apply_migration():
    print(f"🚀 Connecting to database: {DATABASE_URL.split('@')[-1]}")
    
    with engine.connect() as conn:
        print("🔍 Checking if 'scheduled_at' column exists in 'content' table...")
        
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='content' AND column_name='scheduled_at';
        """)).fetchone()
        
        if not result:
            print("➕ Adding 'scheduled_at' column to 'content' table...")
            conn.execute(text("ALTER TABLE content ADD COLUMN scheduled_at TIMESTAMP;"))
            print("✅ Column added successfully.")
        else:
            print("ℹ️ Column 'scheduled_at' already exists.")
            
        conn.commit()

if __name__ == "__main__":
    try:
        apply_migration()
        print("✨ Database schema update complete.")
    except Exception as e:
        print(f"❌ Error updating database: {e}")

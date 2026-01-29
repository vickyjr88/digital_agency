import os
import sys
import psycopg2
from urllib.parse import urlparse

def sync_schema():
    # Use the same logic as the app to find the DATABASE_URL
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url and os.path.exists(".env"):
        print("Reading DATABASE_URL from .env file...")
        with open(".env") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    database_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    
    if not database_url:
        print("❌ Error: DATABASE_URL not found in environment or .env file")
        sys.exit(1)

    print(f"🚀 Syncing schema for database: {urlparse(database_url).path}")
    
    commands = [
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS brand_entity_id VARCHAR(36) REFERENCES brands(id);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS title VARCHAR(255);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS description TEXT;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS budget INTEGER DEFAULT 0;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS budget_spent INTEGER DEFAULT 0;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platforms JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS content_types JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS voice VARCHAR(100);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS sample_tone TEXT;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS key_messages JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS hashtags JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_audience TEXT;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS content_style VARCHAR(50);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS content_themes JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_name VARCHAR(255);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_description TEXT;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_url VARCHAR(500);",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS content_dos JSON;",
        "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS content_donts JSON;",
        "ALTER TABLE campaigns ALTER COLUMN influencer_id DROP NOT NULL;",
        "ALTER TABLE campaigns ALTER COLUMN package_id DROP NOT NULL;"
    ]

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        for cmd in commands:
            try:
                cur.execute(cmd)
                print(f"✅ Success: {cmd[:50]}...")
            except Exception as e:
                print(f"⚠️ Warning: Failed to execute '{cmd[:50]}...': {e}")
        
        cur.close()
        conn.close()
        print("\n✨ Database schema sync completed!")
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_schema()

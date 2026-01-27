import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def check_columns():
    with engine.connect() as conn:
        for table, column in [('content', 'scheduled_at'), ('content', 'meta_data'), ('usage', 'content_generated_count')]:
            result = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='{table}' AND column_name='{column}';
            """)).fetchone()
            if not result:
                print(f"❌ Column '{column}' missing in table '{table}'")
            else:
                print(f"✅ Column '{column}' exists in table '{table}'")

if __name__ == "__main__":
    check_columns()

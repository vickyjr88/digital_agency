
import os
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Try to load dotenv, if available
try:
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment!")
    exit(1)

# Fix for Heroku/Railway style URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# List of (type_name, [expected_lowercase_values])
ENUM_TYPES = [
    ("verificationstatusdb", ["pending", "approved", "rejected"]),
    ("platformtypedb", ["instagram", "tiktok", "youtube", "twitter", "multi"]),
    ("packagestatusdb", ["active", "paused", "deleted"]),
    ("paymentmethodtype", ["mpesa", "airtel_money", "bank_transfer"]),
    ("wallettransactiontypedb", ["deposit", "withdrawal", "escrow_lock", "escrow_release", "escrow_refund", "platform_fee", "transfer"]),
    ("wallettransactionstatusdb", ["pending", "processing", "completed", "failed", "cancelled"]),
    ("escrowstatusdb", ["locked", "released", "refunded", "disputed"]),
    ("campaignstatusdb", ["open", "closed", "pending", "accepted", "in_progress", "draft_submitted", "revision_requested", "draft_approved", "published", "pending_review", "completed", "disputed", "cancelled"]),
    ("deliverablestatusdb", ["pending", "draft", "submitted", "approved", "rejected", "published", "verified"]),
    ("disputestatusdb", ["open", "under_review", "resolved", "closed"]),
    ("bidstatusdb", ["pending", "accepted", "rejected", "withdrawn", "completed", "paid"]),
    ("proofofworkstatus", ["pending", "approved", "rejected", "revision_requested"]),
    ("campaigncontentstatus", ["draft", "submitted", "approved", "published"])
]

# List of (table_name, column_name, type_name)
TABLE_COLUMNS = [
    ("influencer_profiles", "verification_status", "verificationstatusdb"),
    ("bids", "status", "bidstatusdb"),
    ("campaigns", "status", "campaignstatusdb"),
    ("deliverables", "status", "deliverablestatusdb"),
    ("packages", "status", "packagestatusdb"),
    ("wallet_transactions", "transaction_type", "wallettransactiontypedb"),
    ("wallet_transactions", "status", "wallettransactionstatusdb"),
    ("escrow_holds", "status", "escrowstatusdb"),
    ("disputes", "status", "disputestatusdb"),
    ("payment_methods", "method_type", "paymentmethodtype"),
    ("proof_of_work", "status", "proofofworkstatus"),
    ("campaign_content", "status", "campaigncontentstatus")
]

def sync_enums():
    print(f"🚀 Starting Lowercase Enum Sync on {DATABASE_URL.split('@')[-1]}")
    
    # 1. Add lowercase values to ENUM types
    # Postgres ALTER TYPE ADD VALUE cannot run in a transaction
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for type_name, values in ENUM_TYPES:
            print(f"🔍 Checking enum type: {type_name}")
            
            # Get existing values
            res = conn.execute(text(f"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = '{type_name}'"))
            existing_values = [r[0] for r in res]
            
            for val in values:
                if val not in existing_values:
                    print(f"➕ Adding value '{val}' to {type_name}")
                    try:
                        conn.execute(text(f"ALTER TYPE {type_name} ADD VALUE '{val}'"))
                    except Exception as e:
                        print(f"⚠️ Could not add '{val}' to {type_name}: {e}")

    # 2. Update existing data to lowercase
    with engine.begin() as conn:
        for table, column, type_name in TABLE_COLUMNS:
            print(f"🔄 Updating {table}.{column} to lowercase...")
            try:
                # Check if table exists
                table_exists = conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")).scalar()
                if not table_exists:
                    print(f"⏩ Table {table} does not exist, skipping.")
                    continue
                
                # Check if column exists
                col_exists = conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{column}')")).scalar()
                if not col_exists:
                    print(f"⏩ Column {column} in {table} does not exist, skipping.")
                    continue

                # Update rows
                conn.execute(text(f"UPDATE {table} SET {column} = LOWER({column}::text)::{type_name} WHERE {column}::text != LOWER({column}::text)"))
                print(f"✅ Updated {table}.{column}")
            except Exception as e:
                print(f"❌ Failed to update {table}.{column}: {e}")

    print("🎉 Sync complete!")

if __name__ == "__main__":
    sync_enums()

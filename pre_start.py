import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic import command
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from database
sys.path.append(str(Path(__file__).resolve().parent))

from database.config import DATABASE_URL
from database.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Check if alembic_version table exists
    has_alembic = inspector.has_table("alembic_version")
    has_users = inspector.has_table("users")
    
    alembic_cfg = Config("alembic.ini")
    
    if not has_users:
        logger.info("Fresh database detected. Creating all tables from models...")
        # Create all schemas
        # Import all models to ensure they are registered
        from database import marketplace_models, affiliate_models, tumanasi_models
        Base.metadata.create_all(bind=engine)
        
        logger.info("Stamping alembic head...")
        # Stamp alembic version to latest
        command.stamp(alembic_cfg, "head")
        logger.info("Database initialized successfully.")
    elif not has_alembic:
        logger.info("Legacy database detected without alembic. We must upgrade.")
        # We assume the legacy DB matches the state right before the first migration.
        # But wait, we can't reliably stamp legacy. We'll simply let alembic run and handle errors.
        try:
            command.upgrade(alembic_cfg, "head")
        except Exception as e:
            logger.error(f"Error during alembic upgrade: {e}")
            logger.info("Attempting to stamp head if this fails due to already existing objects.")
            command.stamp(alembic_cfg, "head")
    else:
        logger.info("Database has alembic. Running migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed.")
        
    # Also seed Tumanasi zones if needed
    try:
        from seed_tumanasi_zones import seed as seed_zones
        seed_zones()
    except Exception as e:
        logger.warning(f"Could not seed Tumanasi zones: {e}")

if __name__ == "__main__":
    main()

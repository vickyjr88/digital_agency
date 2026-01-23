# Database Configuration and Session Management

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Debug: print the database URL being used
print(f"DATABASE_URL loaded: {os.getenv('DATABASE_URL')}")

# Database URL from environment variable
# Use 'postgres' as host when running in Docker (service name from docker-compose)
# Use 'localhost' when running locally outside Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/dexter")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI
def get_db() -> Session:
    """
    FastAPI dependency to get database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for database session.
    Usage: 
    with get_db_context() as db:
        # do something with db
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    Run this once to create all tables.
    """
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    # Create tables when run directly
    init_db()

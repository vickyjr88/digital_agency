import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Set SQLALCHEMY_DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Escape % characters for ConfigParser (% -> %%)
    escaped_url = DATABASE_URL.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", escaped_url)

# add your model's MetaData object here
# for 'autogenerate' support
# Import all models so Alembic can detect them
from database.models import Base
from database import marketplace_models  # Also import marketplace models

target_metadata = Base.metadata


def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    # Unescape URL for actual use
    if url:
        url = url.replace("%%", "%")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations in 'online' mode.
    """
    # Use the original DATABASE_URL directly to avoid ConfigParser issues
    url = DATABASE_URL
    if not url:
        url = config.get_main_option("sqlalchemy.url")
        if url:
            url = url.replace("%%", "%")
    
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

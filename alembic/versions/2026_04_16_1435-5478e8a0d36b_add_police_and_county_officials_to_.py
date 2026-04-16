"""Add police and county_officials to expense categories

Revision ID: 5478e8a0d36b
Revises: 8d07a6f8d632
Create Date: 2026-04-16 14:35:32.169937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5478e8a0d36b'
down_revision: Union[str, None] = '8d07a6f8d632'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to expensecategorydb enum
    # Note: PostgreSQL doesn't support removing enum values easily, so downgrade won't remove them
    op.execute("ALTER TYPE expensecategorydb ADD VALUE IF NOT EXISTS 'police'")
    op.execute("ALTER TYPE expensecategorydb ADD VALUE IF NOT EXISTS 'county_officials'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values
    # The values will remain in the enum type even after downgrade
    pass

"""Enterprise baseline schema.

Revision ID: 0001_enterprise_baseline
Revises: None
"""
from alembic import op

from core.database import Base
from models import entities  # noqa: F401


revision = "0001_enterprise_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The first migration adopts existing SQLite demo databases without data loss.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Legal case data is never dropped by a generic migration rollback.
    pass


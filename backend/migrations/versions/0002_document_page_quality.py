"""Store page-level extraction quality and OCR regions.

Revision ID: 0002_document_page_quality
Revises: 0001_enterprise_baseline
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0002_document_page_quality"
down_revision = "0001_enterprise_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 adopts databases using metadata.create_all, so a fresh database may
    # already contain this table when it reaches this migration.
    if "document_pages" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "document_pages",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_mode", sa.String(length=30), nullable=False, server_default="native_text"),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("ocr_regions", sa.JSON(), nullable=False),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])


def downgrade() -> None:
    # Case-material provenance is intentionally retained on generic rollback.
    pass

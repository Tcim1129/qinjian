"""Add relational consent receipts table for EmotiMirror.

Revision ID: 0026
Revises: 0025
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_consent_receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("pair_id", sa.UUID(), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="authorized", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_consent_receipts_owner_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"], name="fk_consent_receipts_pair_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consent_receipts_owner_id", "emotimirror_consent_receipts", ["owner_id"])
    op.create_index("ix_consent_receipts_pair_id", "emotimirror_consent_receipts", ["pair_id"])
    op.create_index("ix_consent_receipts_status", "emotimirror_consent_receipts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_consent_receipts_status", table_name="emotimirror_consent_receipts")
    op.drop_index("ix_consent_receipts_pair_id", table_name="emotimirror_consent_receipts")
    op.drop_index("ix_consent_receipts_owner_id", table_name="emotimirror_consent_receipts")
    op.drop_table("emotimirror_consent_receipts")

"""Add expiring encrypted authorized shared content.

Revision ID: 0036
Revises: 0035
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_authorized_shared_contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("key_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("envelope_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="sealed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_reason", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["emotimirror_consent_receipts.id"],
            name="fk_authorized_shared_contents_receipt_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_authorized_shared_contents_owner_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pair_id"], ["pairs.id"], name="fk_authorized_shared_contents_pair_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emotimirror_authorized_shared_contents"),
        sa.CheckConstraint(
            "status IN ('sealed', 'submitted', 'purged')",
            name="ck_authorized_shared_contents_status",
        ),
        sa.CheckConstraint(
            "(status = 'purged' AND ciphertext IS NULL) OR "
            "(status IN ('sealed', 'submitted') AND ciphertext IS NOT NULL)",
            name="ck_authorized_shared_contents_ciphertext_lifecycle",
        ),
        sa.CheckConstraint(
            "artifact_version > 0 AND key_version > 0 AND envelope_version > 0",
            name="ck_authorized_shared_contents_positive_versions",
        ),
    )
    op.create_index(
        "uq_emotimirror_authorized_shared_contents_receipt_id",
        "emotimirror_authorized_shared_contents",
        ["receipt_id"],
        unique=True,
    )
    op.create_index(
        "ix_authorized_shared_contents_owner_id",
        "emotimirror_authorized_shared_contents",
        ["owner_id"],
    )
    op.create_index(
        "ix_authorized_shared_contents_pair_id",
        "emotimirror_authorized_shared_contents",
        ["pair_id"],
    )
    op.create_index(
        "ix_authorized_shared_contents_status",
        "emotimirror_authorized_shared_contents",
        ["status"],
    )
    op.create_index(
        "ix_authorized_shared_contents_expires_at",
        "emotimirror_authorized_shared_contents",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_authorized_shared_contents_expires_at",
        table_name="emotimirror_authorized_shared_contents",
    )
    op.drop_index(
        "ix_authorized_shared_contents_status",
        table_name="emotimirror_authorized_shared_contents",
    )
    op.drop_index(
        "ix_authorized_shared_contents_pair_id",
        table_name="emotimirror_authorized_shared_contents",
    )
    op.drop_index(
        "ix_authorized_shared_contents_owner_id",
        table_name="emotimirror_authorized_shared_contents",
    )
    op.drop_index(
        "uq_emotimirror_authorized_shared_contents_receipt_id",
        table_name="emotimirror_authorized_shared_contents",
    )
    op.drop_table("emotimirror_authorized_shared_contents")

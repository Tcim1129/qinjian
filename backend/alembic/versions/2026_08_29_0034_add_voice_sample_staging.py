"""Add expiring encrypted staging metadata for owner voice samples.

Revision ID: 0034
Revises: 0033
"""

from alembic import op
import sqlalchemy as sa


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_sample_staging",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("consent_id", sa.UUID(), nullable=False),
        sa.Column("voice_asset_id", sa.UUID(), nullable=True),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("access_token_hash", sa.String(length=64), nullable=False),
        sa.Column("sample_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=False),
        sa.Column("sample_width_bits", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_count", sa.Integer(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["emotimirror_voice_clone_consents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["voice_asset_id"],
            ["emotimirror_voice_assets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_path",
            name="uq_emotimirror_voice_sample_staging_storage_path",
        ),
        sa.UniqueConstraint(
            "access_token_hash",
            name="uq_emotimirror_voice_sample_staging_token_hash",
        ),
        sa.UniqueConstraint(
            "voice_asset_id",
            name="uq_emotimirror_voice_sample_staging_asset_id",
        ),
    )
    op.create_index(
        "ix_emotimirror_voice_sample_staging_owner_id",
        "emotimirror_voice_sample_staging",
        ["owner_id"],
    )
    op.create_index(
        "ix_emotimirror_voice_sample_staging_status",
        "emotimirror_voice_sample_staging",
        ["status"],
    )
    op.create_index(
        "ix_emotimirror_voice_sample_staging_expires_at",
        "emotimirror_voice_sample_staging",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emotimirror_voice_sample_staging_expires_at",
        table_name="emotimirror_voice_sample_staging",
    )
    op.drop_index(
        "ix_emotimirror_voice_sample_staging_status",
        table_name="emotimirror_voice_sample_staging",
    )
    op.drop_index(
        "ix_emotimirror_voice_sample_staging_owner_id",
        table_name="emotimirror_voice_sample_staging",
    )
    op.drop_table("emotimirror_voice_sample_staging")


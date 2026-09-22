"""Add independent owner voice-clone consent and provider asset lifecycle.

Revision ID: 0033
Revises: 0032
"""

from alembic import op
import sqlalchemy as sa


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_clone_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.String(length=60), nullable=False),
        sa.Column("terms_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider_asset_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("sample_transfer_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("ai_synthetic_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("ownership_attested", sa.Boolean(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id", name="uq_emotimirror_voice_clone_consents_owner_id"
        ),
    )
    op.create_index(
        "ix_emotimirror_voice_clone_consents_owner_id",
        "emotimirror_voice_clone_consents",
        ["owner_id"],
    )
    op.create_index(
        "ix_emotimirror_voice_clone_consents_status",
        "emotimirror_voice_clone_consents",
        ["status"],
    )

    op.create_table(
        "emotimirror_voice_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("consent_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("region", sa.String(length=40), nullable=False),
        sa.Column("target_model", sa.String(length=100), nullable=False),
        sa.Column("provider_voice_ref_ciphertext", sa.Text(), nullable=True),
        sa.Column("provider_voice_ref_hash", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("provider_request_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_sha256", sa.String(length=64), nullable=False),
        sa.Column("sample_staging_status", sa.String(length=40), nullable=False),
        sa.Column("sample_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_request_id", sa.String(length=100), nullable=True),
        sa.Column("deletion_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_verification_method", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["emotimirror_voice_clone_consents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_voice_ref_hash",
            name="uq_emotimirror_voice_assets_provider_ref_hash",
        ),
        sa.UniqueConstraint(
            "idempotency_key_hash",
            name="uq_emotimirror_voice_assets_idempotency_hash",
        ),
    )
    op.create_index(
        "ix_emotimirror_voice_assets_owner_id",
        "emotimirror_voice_assets",
        ["owner_id"],
    )
    op.create_index(
        "ix_emotimirror_voice_assets_status",
        "emotimirror_voice_assets",
        ["status"],
    )
    op.create_index(
        "ix_emotimirror_voice_assets_consent_id",
        "emotimirror_voice_assets",
        ["consent_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emotimirror_voice_assets_consent_id",
        table_name="emotimirror_voice_assets",
    )
    op.drop_index(
        "ix_emotimirror_voice_assets_status",
        table_name="emotimirror_voice_assets",
    )
    op.drop_index(
        "ix_emotimirror_voice_assets_owner_id",
        table_name="emotimirror_voice_assets",
    )
    op.drop_table("emotimirror_voice_assets")
    op.drop_index(
        "ix_emotimirror_voice_clone_consents_status",
        table_name="emotimirror_voice_clone_consents",
    )
    op.drop_index(
        "ix_emotimirror_voice_clone_consents_owner_id",
        table_name="emotimirror_voice_clone_consents",
    )
    op.drop_table("emotimirror_voice_clone_consents")


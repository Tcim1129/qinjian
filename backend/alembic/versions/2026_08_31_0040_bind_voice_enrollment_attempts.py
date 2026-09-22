"""Add durable voice enrollment attempts before provider side effects.

Revision ID: 0040
Revises: 0039
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


_STATES = (
    "'claimed','provider_in_flight','outcome_unknown','succeeded',"
    "'known_failed','revoked_pending_reconcile','revoked_verified','blocked',"
    "'closed_no_remote','legacy_unverified'"
)


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_enrollment_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_generation", sa.Integer(), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("enrollment_prefix", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_workspace_scope", sa.String(length=64), nullable=False),
        sa.Column("target_model", sa.String(length=100), nullable=False),
        sa.Column("language_hint", sa.String(length=10), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("claim_token_hash", sa.String(length=64), nullable=True),
        sa.Column("provider_request_id", sa.String(length=100), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("provider_call_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_call_deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"state IN ({_STATES})", name="ck_emotimirror_voice_enrollment_attempts_state"),
        sa.CheckConstraint("consent_generation >= 0", name="ck_emotimirror_voice_enrollment_attempts_generation"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consent_id"], ["emotimirror_voice_clone_consents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sample_id"], ["emotimirror_voice_sample_staging.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asset_id"], ["emotimirror_voice_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key_hash", name="uq_emotimirror_voice_enrollment_attempts_idempotency_hash"),
        sa.UniqueConstraint("sample_id", name="uq_emotimirror_voice_enrollment_attempts_sample_id"),
        sa.UniqueConstraint("asset_id", name="uq_emotimirror_voice_enrollment_attempts_asset_id"),
    )
    op.create_index("ix_voice_enrollment_attempts_owner_id", "emotimirror_voice_enrollment_attempts", ["owner_id"])
    op.create_index("ix_voice_enrollment_attempts_state_deadline", "emotimirror_voice_enrollment_attempts", ["state", "provider_call_deadline_at"])


def downgrade() -> None:
    op.drop_index("ix_voice_enrollment_attempts_state_deadline", table_name="emotimirror_voice_enrollment_attempts")
    op.drop_index("ix_voice_enrollment_attempts_owner_id", table_name="emotimirror_voice_enrollment_attempts")
    op.drop_table("emotimirror_voice_enrollment_attempts")

"""Add generation-bound dynamic challenges for owner voice cloning.

Revision ID: 0039
Revises: 0038
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_voice_clone_consents",
        sa.Column("challenge_asr_acknowledged", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "emotimirror_voice_clone_consents",
        sa.Column("grant_generation", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "emotimirror_voice_clone_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_generation", sa.Integer(), nullable=False),
        sa.Column("challenge_text", sa.String(length=180), nullable=False),
        sa.Column("challenge_text_hash", sa.String(length=64), nullable=False),
        sa.Column("challenge_token", sa.String(length=40), nullable=False),
        sa.Column("challenge_token_hash", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("normalized_transcript_hash", sa.String(length=64), nullable=True),
        sa.Column("phrase_match_score", sa.Float(), nullable=True),
        sa.Column("verification_method", sa.String(length=40), nullable=True),
        sa.Column("asr_provider", sa.String(length=40), nullable=True),
        sa.Column("asr_model", sa.String(length=100), nullable=True),
        sa.Column("sample_sha256", sa.String(length=64), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('issued','verified','failed','expired','consumed','revoked')",
            name="ck_emotimirror_voice_clone_challenges_status",
        ),
        sa.ForeignKeyConstraint(["consent_id"], ["emotimirror_voice_clone_consents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_sha256", name="uq_emotimirror_voice_clone_challenges_sample_sha256"),
    )
    op.create_index("ix_emotimirror_voice_clone_challenges_owner_id", "emotimirror_voice_clone_challenges", ["owner_id"])
    op.create_index("ix_emotimirror_voice_clone_challenges_status", "emotimirror_voice_clone_challenges", ["status"])
    op.create_index("ix_emotimirror_voice_clone_challenges_expires_at", "emotimirror_voice_clone_challenges", ["expires_at"])
    op.add_column(
        "emotimirror_voice_sample_staging",
        sa.Column("consent_generation", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("emotimirror_voice_sample_staging", sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("emotimirror_voice_sample_staging", sa.Column("phrase_verification_status", sa.String(length=30), server_default="unverified", nullable=False))
    op.add_column("emotimirror_voice_sample_staging", sa.Column("liveness_status", sa.String(length=30), server_default="unverified", nullable=False))
    op.add_column("emotimirror_voice_sample_staging", sa.Column("replay_detection_status", sa.String(length=30), server_default="unverified", nullable=False))
    op.add_column("emotimirror_voice_sample_staging", sa.Column("speaker_count_status", sa.String(length=30), server_default="unverified", nullable=False))
    op.create_foreign_key("fk_voice_sample_challenge_id", "emotimirror_voice_sample_staging", "emotimirror_voice_clone_challenges", ["challenge_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_emotimirror_voice_sample_staging_challenge_id", "emotimirror_voice_sample_staging", ["challenge_id"])


def downgrade() -> None:
    op.drop_constraint("uq_emotimirror_voice_sample_staging_challenge_id", "emotimirror_voice_sample_staging", type_="unique")
    op.drop_constraint("fk_voice_sample_challenge_id", "emotimirror_voice_sample_staging", type_="foreignkey")
    for column in ("speaker_count_status", "replay_detection_status", "liveness_status", "phrase_verification_status", "challenge_id", "consent_generation"):
        op.drop_column("emotimirror_voice_sample_staging", column)
    op.drop_index("ix_emotimirror_voice_clone_challenges_expires_at", table_name="emotimirror_voice_clone_challenges")
    op.drop_index("ix_emotimirror_voice_clone_challenges_status", table_name="emotimirror_voice_clone_challenges")
    op.drop_index("ix_emotimirror_voice_clone_challenges_owner_id", table_name="emotimirror_voice_clone_challenges")
    op.drop_table("emotimirror_voice_clone_challenges")
    op.drop_column("emotimirror_voice_clone_consents", "grant_generation")
    op.drop_column("emotimirror_voice_clone_consents", "challenge_asr_acknowledged")

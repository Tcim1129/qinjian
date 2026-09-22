"""Add append-only, generation-bound advanced voice evidence.

Revision ID: 0041
Revises: 0040
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_advanced_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_generation", sa.Integer(), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_sha256", sa.String(length=64), nullable=False),
        sa.Column("verifier_provider", sa.String(length=80), nullable=False),
        sa.Column("verifier_model", sa.String(length=120), nullable=False),
        sa.Column("verifier_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=40), nullable=False),
        sa.Column("result_status", sa.String(length=30), nullable=False),
        sa.Column("liveness_status", sa.String(length=30), nullable=False),
        sa.Column("replay_detection_status", sa.String(length=30), nullable=False),
        sa.Column("speaker_count_status", sa.String(length=30), nullable=False),
        sa.Column("liveness_score", sa.Float(), nullable=True),
        sa.Column("replay_risk_score", sa.Float(), nullable=True),
        sa.Column("speaker_count", sa.Integer(), nullable=True),
        sa.Column("thresholds_json", sa.JSON(), nullable=False),
        sa.Column("provider_request_id_hash", sa.String(length=64), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result_status IN ('verified','rejected','indeterminate','error')",
            name="ck_voice_advanced_evidence_result_status",
        ),
        sa.CheckConstraint(
            "consent_generation >= 0",
            name="ck_voice_advanced_evidence_generation",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["emotimirror_voice_clone_consents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["emotimirror_voice_sample_staging.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_voice_advanced_evidence_owner_id",
        "emotimirror_voice_advanced_evidence",
        ["owner_id"],
    )
    op.create_index(
        "ix_voice_advanced_evidence_sample_policy_evaluated",
        "emotimirror_voice_advanced_evidence",
        ["sample_id", "policy_version", "evaluated_at"],
    )
    op.create_index(
        "ix_voice_advanced_evidence_result_expires",
        "emotimirror_voice_advanced_evidence",
        ["result_status", "expires_at"],
    )
    op.add_column(
        "emotimirror_voice_enrollment_attempts",
        sa.Column(
            "advanced_evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_voice_enrollment_attempt_advanced_evidence",
        "emotimirror_voice_enrollment_attempts",
        "emotimirror_voice_advanced_evidence",
        ["advanced_evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        CREATE FUNCTION emotimirror_reject_voice_evidence_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION '声音高级证据为追加式记录，禁止更新';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_voice_advanced_evidence_no_update
        BEFORE UPDATE ON emotimirror_voice_advanced_evidence
        FOR EACH ROW
        EXECUTE FUNCTION emotimirror_reject_voice_evidence_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_voice_advanced_evidence_no_update "
        "ON emotimirror_voice_advanced_evidence"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS emotimirror_reject_voice_evidence_update()"
    )
    op.drop_constraint(
        "fk_voice_enrollment_attempt_advanced_evidence",
        "emotimirror_voice_enrollment_attempts",
        type_="foreignkey",
    )
    op.drop_column(
        "emotimirror_voice_enrollment_attempts", "advanced_evidence_id"
    )
    op.drop_index(
        "ix_voice_advanced_evidence_result_expires",
        table_name="emotimirror_voice_advanced_evidence",
    )
    op.drop_index(
        "ix_voice_advanced_evidence_sample_policy_evaluated",
        table_name="emotimirror_voice_advanced_evidence",
    )
    op.drop_index(
        "ix_voice_advanced_evidence_owner_id",
        table_name="emotimirror_voice_advanced_evidence",
    )
    op.drop_table("emotimirror_voice_advanced_evidence")

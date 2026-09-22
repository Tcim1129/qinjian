"""Persist EmotiMirror voice consent, somatic sessions, and feedback.

Revision ID: 0029
Revises: 0028
"""

from alembic import op
import sqlalchemy as sa


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("consent_granted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retention_policy", sa.String(length=30), server_default="zero_retention", nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", name="uq_emotimirror_voice_consents_owner_id"),
    )
    op.create_index("ix_emotimirror_voice_consents_owner_id", "emotimirror_voice_consents", ["owner_id"])

    op.create_table(
        "emotimirror_somatic_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("protocol_id", sa.String(length=40), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("subjective_feedback", sa.String(length=20), server_default="calmer", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emotimirror_somatic_sessions_owner_id", "emotimirror_somatic_sessions", ["owner_id"])

    op.create_table(
        "emotimirror_feedbacks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=True),
        sa.Column("feedback_type", sa.String(length=40), nullable=False),
        sa.Column("safe_comment", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emotimirror_feedbacks_owner_id", "emotimirror_feedbacks", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_emotimirror_feedbacks_owner_id", table_name="emotimirror_feedbacks")
    op.drop_table("emotimirror_feedbacks")
    op.drop_index("ix_emotimirror_somatic_sessions_owner_id", table_name="emotimirror_somatic_sessions")
    op.drop_table("emotimirror_somatic_sessions")
    op.drop_index("ix_emotimirror_voice_consents_owner_id", table_name="emotimirror_voice_consents")
    op.drop_table("emotimirror_voice_consents")

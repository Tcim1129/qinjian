"""Add EmotiMirror persistence tables for authorship, coordination, and provenance.

Revision ID: 0027
Revises: 0026
"""

from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. emotimirror_authorship_claims
    op.create_table(
        "emotimirror_authorship_claims",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("original_input", sa.Text(), nullable=False),
        sa.Column("ai_suggestion", sa.Text(), nullable=False),
        sa.Column("current_text", sa.Text(), nullable=False),
        sa.Column("user_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("state", sa.String(length=30), server_default="pending_review", nullable=False),
        sa.Column("confirmation_hash", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_authorship_claims_owner_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_authorship_claims_owner_id", "emotimirror_authorship_claims", ["owner_id"])
    op.create_index("ix_authorship_claims_state", "emotimirror_authorship_claims", ["state"])

    # 2. emotimirror_coordination_sessions
    op.create_table(
        "emotimirror_coordination_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pair_id", sa.UUID(), nullable=False),
        sa.Column("initiator_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=30), server_default="initiated", nullable=False),
        sa.Column("party_receipts", sa.JSON(), nullable=True),
        sa.Column("action_agreed", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"], name="fk_coordination_sessions_pair_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiator_id"], ["users.id"], name="fk_coordination_sessions_initiator_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coordination_sessions_pair_id", "emotimirror_coordination_sessions", ["pair_id"])
    op.create_index("ix_coordination_sessions_initiator_id", "emotimirror_coordination_sessions", ["initiator_id"])
    op.create_index("ix_coordination_sessions_state", "emotimirror_coordination_sessions", ["state"])

    # 3. emotimirror_content_provenances
    op.create_table(
        "emotimirror_content_provenances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("original_input", sa.Text(), nullable=False),
        sa.Column("final_text", sa.Text(), nullable=False),
        sa.Column("tag", sa.String(length=40), server_default="direct_user_input", nullable=False),
        sa.Column("user_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_content_provenances_owner_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_provenances_owner_id", "emotimirror_content_provenances", ["owner_id"])
    op.create_index("ix_content_provenances_tag", "emotimirror_content_provenances", ["tag"])


def downgrade() -> None:
    op.drop_index("ix_content_provenances_tag", table_name="emotimirror_content_provenances")
    op.drop_index("ix_content_provenances_owner_id", table_name="emotimirror_content_provenances")
    op.drop_table("emotimirror_content_provenances")

    op.drop_index("ix_coordination_sessions_state", table_name="emotimirror_coordination_sessions")
    op.drop_index("ix_coordination_sessions_initiator_id", table_name="emotimirror_coordination_sessions")
    op.drop_index("ix_coordination_sessions_pair_id", table_name="emotimirror_coordination_sessions")
    op.drop_table("emotimirror_coordination_sessions")

    op.drop_index("ix_authorship_claims_state", table_name="emotimirror_authorship_claims")
    op.drop_index("ix_authorship_claims_owner_id", table_name="emotimirror_authorship_claims")
    op.drop_table("emotimirror_authorship_claims")

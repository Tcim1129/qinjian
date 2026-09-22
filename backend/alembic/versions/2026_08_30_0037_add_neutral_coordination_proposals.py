"""Add privacy-bounded neutral coordination proposals.

Revision ID: 0037
Revises: 0036
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_neutral_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("proposal_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["emotimirror_coordination_sessions.id"],
            name="fk_neutral_proposals_session_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pair_id"], ["pairs.id"],
            name="fk_neutral_proposals_pair_id", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emotimirror_neutral_proposals"),
        sa.UniqueConstraint("session_id", name="uq_neutral_proposals_session_id"),
        sa.CheckConstraint(
            "state IN ('ready', 'invalidated')",
            name="ck_neutral_proposals_state",
        ),
    )
    op.create_index(
        "ix_neutral_proposals_pair_id", "emotimirror_neutral_proposals", ["pair_id"]
    )
    op.create_index(
        "ix_neutral_proposals_state", "emotimirror_neutral_proposals", ["state"]
    )


def downgrade() -> None:
    op.drop_index("ix_neutral_proposals_state", table_name="emotimirror_neutral_proposals")
    op.drop_index("ix_neutral_proposals_pair_id", table_name="emotimirror_neutral_proposals")
    op.drop_table("emotimirror_neutral_proposals")

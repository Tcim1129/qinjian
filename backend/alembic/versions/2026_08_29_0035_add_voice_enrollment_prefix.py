"""Persist server-owned voice enrollment prefix for unknown-result reconciliation.

Revision ID: 0035
Revises: 0034
"""

from alembic import op
import sqlalchemy as sa


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_voice_assets",
        sa.Column("enrollment_prefix", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "emotimirror_voice_assets",
        sa.Column("provider_workspace_scope", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "emotimirror_voice_assets",
        sa.Column(
            "reconcile_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "emotimirror_voice_assets",
        sa.Column("reconciliation_match_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "emotimirror_voice_assets",
        sa.Column("next_reconcile_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_emotimirror_voice_assets_provider_prefix",
        "emotimirror_voice_assets",
        ["provider", "provider_workspace_scope", "target_model", "enrollment_prefix"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_emotimirror_voice_assets_provider_prefix",
        table_name="emotimirror_voice_assets",
    )
    op.drop_column("emotimirror_voice_assets", "next_reconcile_at")
    op.drop_column("emotimirror_voice_assets", "reconciliation_match_count")
    op.drop_column("emotimirror_voice_assets", "reconcile_attempts")
    op.drop_column("emotimirror_voice_assets", "provider_workspace_scope")
    op.drop_column("emotimirror_voice_assets", "enrollment_prefix")

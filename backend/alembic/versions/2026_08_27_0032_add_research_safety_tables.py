"""Add missing P5 self-report fields and P7 privacy accounting tables.

Revision ID: 0032
Revises: 0031
"""

from alembic import op
import sqlalchemy as sa


revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_somatic_sessions",
        sa.Column("pre_stress_level", sa.Integer(), nullable=True),
    )
    op.add_column(
        "emotimirror_somatic_sessions",
        sa.Column("post_stress_level", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "emotimirror_somatic_sessions",
        "subjective_feedback",
        existing_type=sa.String(length=20),
        server_default="unchanged",
        existing_nullable=False,
    )

    op.create_table(
        "emotimirror_dp_budget_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("epsilon_consumed", sa.Float(), nullable=False),
        sa.Column("purpose", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("remaining_budget", sa.Float(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_emotimirror_dp_budget_ledger_timestamp",
        "emotimirror_dp_budget_ledger",
        ["timestamp"],
    )

    op.create_table(
        "emotimirror_dp_revocations",
        sa.Column("subject_pseudonym", sa.String(length=64), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("subject_pseudonym"),
    )


def downgrade() -> None:
    op.drop_table("emotimirror_dp_revocations")
    op.drop_index(
        "ix_emotimirror_dp_budget_ledger_timestamp",
        table_name="emotimirror_dp_budget_ledger",
    )
    op.drop_table("emotimirror_dp_budget_ledger")
    op.alter_column(
        "emotimirror_somatic_sessions",
        "subjective_feedback",
        existing_type=sa.String(length=20),
        server_default="calmer",
        existing_nullable=False,
    )
    op.drop_column("emotimirror_somatic_sessions", "post_stress_level")
    op.drop_column("emotimirror_somatic_sessions", "pre_stress_level")

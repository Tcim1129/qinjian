"""add intervention policy library

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "intervention_policy_library" not in existing_tables:
        op.create_table(
            "intervention_policy_library",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("policy_id", sa.String(length=80), nullable=False),
            sa.Column("plan_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("branch", sa.String(length=30), nullable=False),
            sa.Column("branch_label", sa.String(length=50), nullable=False),
            sa.Column("intensity", sa.String(length=20), nullable=False),
            sa.Column("intensity_label", sa.String(length=50), nullable=False),
            sa.Column("copy_mode", sa.String(length=20), nullable=True),
            sa.Column("copy_mode_label", sa.String(length=50), nullable=True),
            sa.Column("when_to_use", sa.Text(), nullable=False),
            sa.Column("success_marker", sa.Text(), nullable=False),
            sa.Column("guardrail", sa.Text(), nullable=False),
            sa.Column(
                "version",
                sa.String(length=20),
                nullable=False,
                server_default="v1",
            ),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "source",
                sa.String(length=20),
                nullable=False,
                server_default="seed",
            ),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {
        index["name"] for index in inspector.get_indexes("intervention_policy_library")
    }
    if op.f("ix_intervention_policy_library_policy_id") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_policy_id"),
            "intervention_policy_library",
            ["policy_id"],
            unique=True,
        )
    if op.f("ix_intervention_policy_library_plan_type") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_plan_type"),
            "intervention_policy_library",
            ["plan_type"],
            unique=False,
        )
    if op.f("ix_intervention_policy_library_branch") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_branch"),
            "intervention_policy_library",
            ["branch"],
            unique=False,
        )
    if op.f("ix_intervention_policy_library_intensity") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_intensity"),
            "intervention_policy_library",
            ["intensity"],
            unique=False,
        )
    if op.f("ix_intervention_policy_library_copy_mode") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_copy_mode"),
            "intervention_policy_library",
            ["copy_mode"],
            unique=False,
        )
    if op.f("ix_intervention_policy_library_status") not in indexes:
        op.create_index(
            op.f("ix_intervention_policy_library_status"),
            "intervention_policy_library",
            ["status"],
            unique=False,
        )
    if "ix_intervention_policy_library_plan_status" not in indexes:
        op.create_index(
            "ix_intervention_policy_library_plan_status",
            "intervention_policy_library",
            ["plan_type", "status", "sort_order"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_intervention_policy_library_plan_status",
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_status"),
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_copy_mode"),
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_intensity"),
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_branch"),
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_plan_type"),
        table_name="intervention_policy_library",
    )
    op.drop_index(
        op.f("ix_intervention_policy_library_policy_id"),
        table_name="intervention_policy_library",
    )
    op.drop_table("intervention_policy_library")

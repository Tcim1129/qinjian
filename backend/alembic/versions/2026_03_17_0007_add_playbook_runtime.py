"""add playbook runtime tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "playbook_runs" not in existing_tables:
        op.create_table(
            "playbook_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("plan_type", sa.String(length=50), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "current_day",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column(
                "active_branch",
                sa.String(length=30),
                nullable=False,
                server_default="steady",
            ),
            sa.Column("branch_reason", sa.Text(), nullable=True),
            sa.Column("branch_started_at", sa.DateTime(), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("last_viewed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "transition_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["plan_id"], ["intervention_plans.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plan_id"),
        )

    run_indexes = {index["name"] for index in inspector.get_indexes("playbook_runs")}
    if op.f("ix_playbook_runs_pair_id") not in run_indexes:
        op.create_index(
            op.f("ix_playbook_runs_pair_id"),
            "playbook_runs",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_playbook_runs_user_id") not in run_indexes:
        op.create_index(
            op.f("ix_playbook_runs_user_id"),
            "playbook_runs",
            ["user_id"],
            unique=False,
        )
    if op.f("ix_playbook_runs_plan_type") not in run_indexes:
        op.create_index(
            op.f("ix_playbook_runs_plan_type"),
            "playbook_runs",
            ["plan_type"],
            unique=False,
        )
    if op.f("ix_playbook_runs_status") not in run_indexes:
        op.create_index(
            op.f("ix_playbook_runs_status"),
            "playbook_runs",
            ["status"],
            unique=False,
        )
    if op.f("ix_playbook_runs_active_branch") not in run_indexes:
        op.create_index(
            op.f("ix_playbook_runs_active_branch"),
            "playbook_runs",
            ["active_branch"],
            unique=False,
        )
    if "ix_playbook_runs_scope_status" not in run_indexes:
        op.create_index(
            "ix_playbook_runs_scope_status",
            "playbook_runs",
            ["pair_id", "user_id", "status"],
            unique=False,
        )

    if "playbook_transitions" not in existing_tables:
        op.create_table(
            "playbook_transitions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "transition_type",
                sa.String(length=40),
                nullable=False,
                server_default="initialized",
            ),
            sa.Column(
                "trigger_type",
                sa.String(length=40),
                nullable=False,
                server_default="run_started",
            ),
            sa.Column("trigger_summary", sa.Text(), nullable=True),
            sa.Column("from_day", sa.Integer(), nullable=True),
            sa.Column(
                "to_day",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column("from_branch", sa.String(length=30), nullable=True),
            sa.Column("to_branch", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["plan_id"], ["intervention_plans.id"]),
            sa.ForeignKeyConstraint(["run_id"], ["playbook_runs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    transition_indexes = {
        index["name"] for index in inspector.get_indexes("playbook_transitions")
    }
    if op.f("ix_playbook_transitions_run_id") not in transition_indexes:
        op.create_index(
            op.f("ix_playbook_transitions_run_id"),
            "playbook_transitions",
            ["run_id"],
            unique=False,
        )
    if op.f("ix_playbook_transitions_plan_id") not in transition_indexes:
        op.create_index(
            op.f("ix_playbook_transitions_plan_id"),
            "playbook_transitions",
            ["plan_id"],
            unique=False,
        )
    if op.f("ix_playbook_transitions_pair_id") not in transition_indexes:
        op.create_index(
            op.f("ix_playbook_transitions_pair_id"),
            "playbook_transitions",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_playbook_transitions_user_id") not in transition_indexes:
        op.create_index(
            op.f("ix_playbook_transitions_user_id"),
            "playbook_transitions",
            ["user_id"],
            unique=False,
        )
    if "ix_playbook_transitions_run_created" not in transition_indexes:
        op.create_index(
            "ix_playbook_transitions_run_created",
            "playbook_transitions",
            ["run_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_playbook_transitions_run_created",
        table_name="playbook_transitions",
    )
    op.drop_index(
        op.f("ix_playbook_transitions_user_id"),
        table_name="playbook_transitions",
    )
    op.drop_index(
        op.f("ix_playbook_transitions_pair_id"),
        table_name="playbook_transitions",
    )
    op.drop_index(
        op.f("ix_playbook_transitions_plan_id"),
        table_name="playbook_transitions",
    )
    op.drop_index(
        op.f("ix_playbook_transitions_run_id"),
        table_name="playbook_transitions",
    )
    op.drop_table("playbook_transitions")

    op.drop_index("ix_playbook_runs_scope_status", table_name="playbook_runs")
    op.drop_index(op.f("ix_playbook_runs_active_branch"), table_name="playbook_runs")
    op.drop_index(op.f("ix_playbook_runs_status"), table_name="playbook_runs")
    op.drop_index(op.f("ix_playbook_runs_plan_type"), table_name="playbook_runs")
    op.drop_index(op.f("ix_playbook_runs_user_id"), table_name="playbook_runs")
    op.drop_index(op.f("ix_playbook_runs_pair_id"), table_name="playbook_runs")
    op.drop_table("playbook_runs")

"""add relationship intelligence tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "relationship_events" not in existing_tables:
        op.create_table(
            "relationship_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=True),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("source", sa.String(length=30), nullable=False, server_default="system"),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("idempotency_key", sa.String(length=100), nullable=True),
            sa.Column("occurred_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
        )

    event_indexes = {
        index["name"] for index in inspector.get_indexes("relationship_events")
    }
    if op.f("ix_relationship_events_pair_id") not in event_indexes:
        op.create_index(
            op.f("ix_relationship_events_pair_id"),
            "relationship_events",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_relationship_events_user_id") not in event_indexes:
        op.create_index(
            op.f("ix_relationship_events_user_id"),
            "relationship_events",
            ["user_id"],
            unique=False,
        )
    if op.f("ix_relationship_events_event_type") not in event_indexes:
        op.create_index(
            op.f("ix_relationship_events_event_type"),
            "relationship_events",
            ["event_type"],
            unique=False,
        )
    if op.f("ix_relationship_events_occurred_at") not in event_indexes:
        op.create_index(
            op.f("ix_relationship_events_occurred_at"),
            "relationship_events",
            ["occurred_at"],
            unique=False,
        )
    if "ix_relationship_events_pair_occurred" not in event_indexes:
        op.create_index(
            "ix_relationship_events_pair_occurred",
            "relationship_events",
            ["pair_id", "occurred_at"],
            unique=False,
        )
    if "ix_relationship_events_user_occurred" not in event_indexes:
        op.create_index(
            "ix_relationship_events_user_occurred",
            "relationship_events",
            ["user_id", "occurred_at"],
            unique=False,
        )

    if "relationship_profile_snapshots" not in existing_tables:
        op.create_table(
            "relationship_profile_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("window_days", sa.Integer(), nullable=False),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("metrics_json", sa.JSON(), nullable=False),
            sa.Column("risk_summary", sa.JSON(), nullable=True),
            sa.Column("attachment_summary", sa.JSON(), nullable=True),
            sa.Column("suggested_focus", sa.JSON(), nullable=True),
            sa.Column("generated_from_event_at", sa.DateTime(), nullable=True),
            sa.Column("version", sa.String(length=30), nullable=False, server_default="v1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    profile_indexes = {
        index["name"] for index in inspector.get_indexes("relationship_profile_snapshots")
    }
    if op.f("ix_relationship_profile_snapshots_pair_id") not in profile_indexes:
        op.create_index(
            op.f("ix_relationship_profile_snapshots_pair_id"),
            "relationship_profile_snapshots",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_relationship_profile_snapshots_user_id") not in profile_indexes:
        op.create_index(
            op.f("ix_relationship_profile_snapshots_user_id"),
            "relationship_profile_snapshots",
            ["user_id"],
            unique=False,
        )
    if op.f("ix_relationship_profile_snapshots_window_days") not in profile_indexes:
        op.create_index(
            op.f("ix_relationship_profile_snapshots_window_days"),
            "relationship_profile_snapshots",
            ["window_days"],
            unique=False,
        )
    if op.f("ix_relationship_profile_snapshots_snapshot_date") not in profile_indexes:
        op.create_index(
            op.f("ix_relationship_profile_snapshots_snapshot_date"),
            "relationship_profile_snapshots",
            ["snapshot_date"],
            unique=False,
        )
    if "ix_relationship_profile_scope_window_date" not in profile_indexes:
        op.create_index(
            "ix_relationship_profile_scope_window_date",
            "relationship_profile_snapshots",
            ["pair_id", "user_id", "window_days", "snapshot_date"],
            unique=False,
        )

    if "intervention_plans" not in existing_tables:
        op.create_table(
            "intervention_plans",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("plan_type", sa.String(length=50), nullable=False),
            sa.Column("trigger_event_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("trigger_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="none"),
            sa.Column("goal_json", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("owner_version", sa.String(length=30), nullable=False, server_default="v1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["trigger_event_id"], ["relationship_events.id"]),
            sa.ForeignKeyConstraint(
                ["trigger_snapshot_id"], ["relationship_profile_snapshots.id"]
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    plan_indexes = {
        index["name"] for index in inspector.get_indexes("intervention_plans")
    }
    if op.f("ix_intervention_plans_pair_id") not in plan_indexes:
        op.create_index(
            op.f("ix_intervention_plans_pair_id"),
            "intervention_plans",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_intervention_plans_user_id") not in plan_indexes:
        op.create_index(
            op.f("ix_intervention_plans_user_id"),
            "intervention_plans",
            ["user_id"],
            unique=False,
        )
    if op.f("ix_intervention_plans_plan_type") not in plan_indexes:
        op.create_index(
            op.f("ix_intervention_plans_plan_type"),
            "intervention_plans",
            ["plan_type"],
            unique=False,
        )
    if op.f("ix_intervention_plans_status") not in plan_indexes:
        op.create_index(
            op.f("ix_intervention_plans_status"),
            "intervention_plans",
            ["status"],
            unique=False,
        )
    if "ix_intervention_plans_scope_status" not in plan_indexes:
        op.create_index(
            "ix_intervention_plans_scope_status",
            "intervention_plans",
            ["pair_id", "user_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_intervention_plans_scope_status", table_name="intervention_plans")
    op.drop_index(op.f("ix_intervention_plans_status"), table_name="intervention_plans")
    op.drop_index(op.f("ix_intervention_plans_plan_type"), table_name="intervention_plans")
    op.drop_index(op.f("ix_intervention_plans_user_id"), table_name="intervention_plans")
    op.drop_index(op.f("ix_intervention_plans_pair_id"), table_name="intervention_plans")
    op.drop_table("intervention_plans")

    op.drop_index(
        "ix_relationship_profile_scope_window_date",
        table_name="relationship_profile_snapshots",
    )
    op.drop_index(
        op.f("ix_relationship_profile_snapshots_snapshot_date"),
        table_name="relationship_profile_snapshots",
    )
    op.drop_index(
        op.f("ix_relationship_profile_snapshots_window_days"),
        table_name="relationship_profile_snapshots",
    )
    op.drop_index(
        op.f("ix_relationship_profile_snapshots_user_id"),
        table_name="relationship_profile_snapshots",
    )
    op.drop_index(
        op.f("ix_relationship_profile_snapshots_pair_id"),
        table_name="relationship_profile_snapshots",
    )
    op.drop_table("relationship_profile_snapshots")

    op.drop_index(
        "ix_relationship_events_user_occurred", table_name="relationship_events"
    )
    op.drop_index(
        "ix_relationship_events_pair_occurred", table_name="relationship_events"
    )
    op.drop_index(op.f("ix_relationship_events_occurred_at"), table_name="relationship_events")
    op.drop_index(op.f("ix_relationship_events_event_type"), table_name="relationship_events")
    op.drop_index(op.f("ix_relationship_events_user_id"), table_name="relationship_events")
    op.drop_index(op.f("ix_relationship_events_pair_id"), table_name="relationship_events")
    op.drop_table("relationship_events")

"""add pair change requests

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


pair_change_kind_enum = postgresql.ENUM(
    "join_request",
    "type_change",
    name="pairchangerequestkind",
)
pair_change_kind_enum_ref = postgresql.ENUM(
    "join_request",
    "type_change",
    name="pairchangerequestkind",
    create_type=False,
)
pair_change_status_enum = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "cancelled",
    name="pairchangerequeststatus",
)
pair_change_status_enum_ref = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "cancelled",
    name="pairchangerequeststatus",
    create_type=False,
)
pair_type_enum = postgresql.ENUM(
    "couple",
    "friend",
    "spouse",
    "bestfriend",
    "parent",
    name="pairtype",
    create_type=False,
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "pair_change_requests" not in tables:
        pair_change_kind_enum.create(conn, checkfirst=True)
        pair_change_status_enum.create(conn, checkfirst=True)
        op.create_table(
            "pair_change_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("kind", pair_change_kind_enum_ref, nullable=False),
            sa.Column("status", pair_change_status_enum_ref, nullable=False),
            sa.Column("requested_type", pair_type_enum, nullable=True),
            sa.Column(
                "requester_user_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(
                "approver_user_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_pair_change_requests_pair_id"),
            "pair_change_requests",
            ["pair_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pair_change_requests_kind"),
            "pair_change_requests",
            ["kind"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pair_change_requests_status"),
            "pair_change_requests",
            ["status"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pair_change_requests_requester_user_id"),
            "pair_change_requests",
            ["requester_user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pair_change_requests_approver_user_id"),
            "pair_change_requests",
            ["approver_user_id"],
            unique=False,
        )

    if "pairs" in tables:
        with op.batch_alter_table("pairs") as batch_op:
            batch_op.alter_column("type", existing_type=pair_type_enum, nullable=True)

    if "user_notifications" in tables:
        columns = {column["name"] for column in inspector.get_columns("user_notifications")}
        if "target_path" not in columns:
            op.add_column(
                "user_notifications",
                sa.Column("target_path", sa.String(length=255), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "user_notifications" in tables:
        columns = {column["name"] for column in inspector.get_columns("user_notifications")}
        if "target_path" in columns:
            op.drop_column("user_notifications", "target_path")

    if "pairs" in tables:
        with op.batch_alter_table("pairs") as batch_op:
            batch_op.alter_column("type", existing_type=pair_type_enum, nullable=False)

    if "pair_change_requests" in tables:
        op.drop_index(op.f("ix_pair_change_requests_approver_user_id"), table_name="pair_change_requests")
        op.drop_index(op.f("ix_pair_change_requests_requester_user_id"), table_name="pair_change_requests")
        op.drop_index(op.f("ix_pair_change_requests_status"), table_name="pair_change_requests")
        op.drop_index(op.f("ix_pair_change_requests_kind"), table_name="pair_change_requests")
        op.drop_index(op.f("ix_pair_change_requests_pair_id"), table_name="pair_change_requests")
        op.drop_table("pair_change_requests")

    pair_change_status_enum.drop(conn, checkfirst=True)
    pair_change_kind_enum.drop(conn, checkfirst=True)

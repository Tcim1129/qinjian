"""add break request retention flow

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


pair_change_phase_enum = postgresql.ENUM(
    "awaiting_timeout",
    "awaiting_retention_choice",
    "retaining",
    name="pairchangerequestphase",
)
pair_change_phase_enum_ref = postgresql.ENUM(
    "awaiting_timeout",
    "awaiting_retention_choice",
    "retaining",
    name="pairchangerequestphase",
    create_type=False,
)
pair_change_resolution_reason_enum = postgresql.ENUM(
    "no_retention_timeout",
    "partner_declined",
    "choice_timeout",
    "retention_rejected",
    "retention_timeout",
    "retention_accepted",
    "requester_cancelled",
    name="pairchangerequestresolutionreason",
)
pair_change_resolution_reason_enum_ref = postgresql.ENUM(
    "no_retention_timeout",
    "partner_declined",
    "choice_timeout",
    "retention_rejected",
    "retention_timeout",
    "retention_accepted",
    "requester_cancelled",
    name="pairchangerequestresolutionreason",
    create_type=False,
)


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _enum_exists(conn, enum_name: str) -> bool:
    if conn.dialect.name != "postgresql":
        return False
    query = sa.text(
        "select 1 from pg_type where typname = :enum_name limit 1"
    )
    return bool(conn.execute(query, {"enum_name": enum_name}).scalar())


def _enum_value_exists(conn, enum_name: str, value: str) -> bool:
    query = sa.text(
        """
        select 1
        from pg_enum e
        join pg_type t on t.oid = e.enumtypid
        where t.typname = :enum_name and e.enumlabel = :value
        limit 1
        """
    )
    return bool(conn.execute(query, {"enum_name": enum_name, "value": value}).scalar())


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    dialect = conn.dialect.name

    if "pair_change_requests" in tables:
        if dialect == "postgresql" and not _enum_value_exists(
            conn, "pairchangerequestkind", "break_request"
        ):
            op.execute("ALTER TYPE pairchangerequestkind ADD VALUE 'break_request'")

        if dialect == "postgresql":
            pair_change_phase_enum.create(conn, checkfirst=True)
            pair_change_resolution_reason_enum.create(conn, checkfirst=True)

        if not _has_column(inspector, "pair_change_requests", "allow_retention"):
            op.add_column(
                "pair_change_requests",
                sa.Column(
                    "allow_retention",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )

        if not _has_column(inspector, "pair_change_requests", "phase"):
            op.add_column(
                "pair_change_requests",
                sa.Column(
                    "phase",
                    pair_change_phase_enum_ref
                    if dialect == "postgresql"
                    else sa.String(length=50),
                    nullable=True,
                ),
            )

        if not _has_column(inspector, "pair_change_requests", "expires_at"):
            op.add_column(
                "pair_change_requests",
                sa.Column("expires_at", sa.DateTime(), nullable=True),
            )

        if not _has_column(inspector, "pair_change_requests", "resolution_reason"):
            op.add_column(
                "pair_change_requests",
                sa.Column(
                    "resolution_reason",
                    pair_change_resolution_reason_enum_ref
                    if dialect == "postgresql"
                    else sa.String(length=50),
                    nullable=True,
                ),
            )

    if "pair_change_request_messages" not in tables:
        op.create_table(
            "pair_change_request_messages",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(length=36),
                nullable=False,
            ),
            sa.Column(
                "request_id",
                postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(length=36),
                nullable=False,
            ),
            sa.Column(
                "sender_user_id",
                postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(length=36),
                nullable=False,
            ),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["pair_change_requests.id"]),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_pair_change_request_messages_request_id"),
            "pair_change_request_messages",
            ["request_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pair_change_request_messages_sender_user_id"),
            "pair_change_request_messages",
            ["sender_user_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    dialect = conn.dialect.name

    if "pair_change_request_messages" in tables:
        op.drop_index(
            op.f("ix_pair_change_request_messages_sender_user_id"),
            table_name="pair_change_request_messages",
        )
        op.drop_index(
            op.f("ix_pair_change_request_messages_request_id"),
            table_name="pair_change_request_messages",
        )
        op.drop_table("pair_change_request_messages")

    if "pair_change_requests" in tables:
        columns = {column["name"] for column in inspector.get_columns("pair_change_requests")}
        if "resolution_reason" in columns:
            op.drop_column("pair_change_requests", "resolution_reason")
        if "expires_at" in columns:
            op.drop_column("pair_change_requests", "expires_at")
        if "phase" in columns:
            op.drop_column("pair_change_requests", "phase")
        if "allow_retention" in columns:
            op.drop_column("pair_change_requests", "allow_retention")

    if dialect == "postgresql":
        if _enum_exists(conn, "pairchangerequestresolutionreason"):
            pair_change_resolution_reason_enum.drop(conn, checkfirst=True)
        if _enum_exists(conn, "pairchangerequestphase"):
            pair_change_phase_enum.drop(conn, checkfirst=True)
        # PostgreSQL does not support removing enum values safely here, so
        # pairchangerequestkind.break_request is intentionally kept.

"""新增用户交互事件表

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# Alembic 版本标识
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "user_interaction_events" in existing_tables:
        return

    op.create_table(
        "user_interaction_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "pair_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pairs.id"),
            nullable=True,
        ),
        sa.Column("session_id", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("page", sa.String(length=80), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("http_method", sa.String(length=12), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_user_interaction_events_user_id",
        "user_interaction_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_pair_id",
        "user_interaction_events",
        ["pair_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_session_id",
        "user_interaction_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_source",
        "user_interaction_events",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_event_type",
        "user_interaction_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_page",
        "user_interaction_events",
        ["page"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_path",
        "user_interaction_events",
        ["path"],
        unique=False,
    )
    op.create_index(
        "ix_user_interaction_events_occurred_at",
        "user_interaction_events",
        ["occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_interaction_events_occurred_at",
        table_name="user_interaction_events",
    )
    op.drop_index("ix_user_interaction_events_path", table_name="user_interaction_events")
    op.drop_index("ix_user_interaction_events_page", table_name="user_interaction_events")
    op.drop_index(
        "ix_user_interaction_events_event_type",
        table_name="user_interaction_events",
    )
    op.drop_index(
        "ix_user_interaction_events_source",
        table_name="user_interaction_events",
    )
    op.drop_index(
        "ix_user_interaction_events_session_id",
        table_name="user_interaction_events",
    )
    op.drop_index("ix_user_interaction_events_pair_id", table_name="user_interaction_events")
    op.drop_index("ix_user_interaction_events_user_id", table_name="user_interaction_events")
    op.drop_table("user_interaction_events")

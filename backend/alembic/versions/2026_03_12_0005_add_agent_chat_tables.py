"""add agent chat tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "agent_chat_sessions" not in existing_tables:
        op.create_table(
            "agent_chat_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "status", sa.String(length=20), server_default="active", nullable=False
            ),
            sa.Column(
                "has_extracted_checkin",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    session_indexes = {
        index["name"] for index in inspector.get_indexes("agent_chat_sessions")
    }
    if op.f("ix_agent_chat_sessions_pair_id") not in session_indexes:
        op.create_index(
            op.f("ix_agent_chat_sessions_pair_id"),
            "agent_chat_sessions",
            ["pair_id"],
            unique=False,
        )
    if op.f("ix_agent_chat_sessions_user_id") not in session_indexes:
        op.create_index(
            op.f("ix_agent_chat_sessions_user_id"),
            "agent_chat_sessions",
            ["user_id"],
            unique=False,
        )

    if "agent_chat_messages" not in existing_tables:
        op.create_table(
            "agent_chat_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["agent_chat_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    message_indexes = {
        index["name"] for index in inspector.get_indexes("agent_chat_messages")
    }
    if op.f("ix_agent_chat_messages_session_id") not in message_indexes:
        op.create_index(
            op.f("ix_agent_chat_messages_session_id"),
            "agent_chat_messages",
            ["session_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_agent_chat_messages_session_id"), table_name="agent_chat_messages"
    )
    op.drop_table("agent_chat_messages")
    op.drop_index(
        op.f("ix_agent_chat_sessions_user_id"), table_name="agent_chat_sessions"
    )
    op.drop_index(
        op.f("ix_agent_chat_sessions_pair_id"), table_name="agent_chat_sessions"
    )
    op.drop_table("agent_chat_sessions")

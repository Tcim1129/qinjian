"""add agent session memory fields

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "agent_chat_sessions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("agent_chat_sessions")}

    if "expires_at" not in columns:
        op.add_column(
            "agent_chat_sessions",
            sa.Column("expires_at", sa.DateTime(), nullable=True),
        )
    if "summary_json" not in columns:
        op.add_column(
            "agent_chat_sessions",
            sa.Column("summary_json", sa.JSON(), nullable=True),
        )
    if "summary_updated_at" not in columns:
        op.add_column(
            "agent_chat_sessions",
            sa.Column("summary_updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "agent_chat_sessions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("agent_chat_sessions")}

    if "summary_updated_at" in columns:
        op.drop_column("agent_chat_sessions", "summary_updated_at")
    if "summary_json" in columns:
        op.drop_column("agent_chat_sessions", "summary_json")
    if "expires_at" in columns:
        op.drop_column("agent_chat_sessions", "expires_at")

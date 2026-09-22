"""Separate chat and check-in Agent session scopes.

Revision ID: 0030
Revises: 0029
"""

from alembic import op
import sqlalchemy as sa


revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_chat_sessions",
        sa.Column(
            "surface",
            sa.String(length=30),
            server_default="checkin_assist",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_agent_chat_sessions_surface",
        "agent_chat_sessions",
        ["surface"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_chat_sessions_surface",
        table_name="agent_chat_sessions",
    )
    op.drop_column("agent_chat_sessions", "surface")

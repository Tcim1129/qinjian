"""Add run grouping and minimal step metadata to agent thoughts.

Revision ID: 0025
Revises: 0024
"""

from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_thoughts", sa.Column("run_id", sa.UUID(), nullable=True))
    op.add_column("agent_thoughts", sa.Column("message_id", sa.UUID(), nullable=True))
    op.add_column("agent_thoughts", sa.Column("phase", sa.String(length=20), nullable=True))
    op.add_column("agent_thoughts", sa.Column("step_status", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_agent_thoughts_message_id", "agent_thoughts", "agent_chat_messages", ["message_id"], ["id"]
    )
    op.create_index("ix_agent_thoughts_run_id", "agent_thoughts", ["run_id"])
    op.create_index("ix_agent_thoughts_message_id", "agent_thoughts", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_thoughts_message_id", table_name="agent_thoughts")
    op.drop_index("ix_agent_thoughts_run_id", table_name="agent_thoughts")
    op.drop_constraint("fk_agent_thoughts_message_id", "agent_thoughts", type_="foreignkey")
    op.drop_column("agent_thoughts", "step_status")
    op.drop_column("agent_thoughts", "phase")
    op.drop_column("agent_thoughts", "message_id")
    op.drop_column("agent_thoughts", "run_id")

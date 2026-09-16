"""add manual task fields

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_tasks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("relationship_tasks")}

    if "source" not in columns:
        op.add_column(
            "relationship_tasks",
            sa.Column("source", sa.String(length=20), nullable=True, server_default="system"),
        )
    if "created_by_user_id" not in columns:
        op.add_column(
            "relationship_tasks",
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "parent_task_id" not in columns:
        op.add_column(
            "relationship_tasks",
            sa.Column("parent_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    op.execute(
        "UPDATE relationship_tasks SET source = 'system' WHERE source IS NULL OR source = ''"
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_tasks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("relationship_tasks")}
    if "parent_task_id" in columns:
        op.drop_column("relationship_tasks", "parent_task_id")
    if "created_by_user_id" in columns:
        op.drop_column("relationship_tasks", "created_by_user_id")
    if "source" in columns:
        op.drop_column("relationship_tasks", "source")

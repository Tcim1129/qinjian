"""add task planner settings and priority

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "pairs" in tables:
        pair_columns = {column["name"] for column in inspector.get_columns("pairs")}
        if "task_planner_settings" not in pair_columns:
            op.add_column(
                "pairs",
                sa.Column("task_planner_settings", sa.JSON(), nullable=True),
            )

    if "relationship_tasks" in tables:
        task_columns = {
            column["name"] for column in inspector.get_columns("relationship_tasks")
        }
        if "importance_level" not in task_columns:
            if conn.dialect.name == "postgresql":
                op.execute(
                    "DO $$ BEGIN "
                    "CREATE TYPE taskimportance AS ENUM ('low', 'medium', 'high'); "
                    "EXCEPTION WHEN duplicate_object THEN NULL; "
                    "END $$;"
                )
            op.add_column(
                "relationship_tasks",
                sa.Column(
                    "importance_level",
                    sa.Enum(
                        "low",
                        "medium",
                        "high",
                        name="taskimportance",
                        native_enum=conn.dialect.name == "postgresql",
                    ),
                    nullable=False,
                    server_default="medium",
                ),
            )
            empty_importance_clause = (
                "importance_level::text = ''"
                if conn.dialect.name == "postgresql"
                else "importance_level = ''"
            )
            op.execute(
                "UPDATE relationship_tasks SET importance_level = 'medium' "
                f"WHERE importance_level IS NULL OR {empty_importance_clause}"
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "relationship_tasks" in tables:
        task_columns = {
            column["name"] for column in inspector.get_columns("relationship_tasks")
        }
        if "importance_level" in task_columns:
            op.drop_column("relationship_tasks", "importance_level")
        if conn.dialect.name == "postgresql":
            op.execute("DROP TYPE IF EXISTS taskimportance")

    if "pairs" in tables:
        pair_columns = {column["name"] for column in inspector.get_columns("pairs")}
        if "task_planner_settings" in pair_columns:
            op.drop_column("pairs", "task_planner_settings")

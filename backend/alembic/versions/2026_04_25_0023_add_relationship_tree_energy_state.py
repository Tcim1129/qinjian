"""add relationship tree energy state

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_trees" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("relationship_trees")}
    if "energy_state" not in columns:
        op.add_column(
            "relationship_trees",
            sa.Column("energy_state", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_trees" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("relationship_trees")}
    if "energy_state" in columns:
        op.drop_column("relationship_trees", "energy_state")

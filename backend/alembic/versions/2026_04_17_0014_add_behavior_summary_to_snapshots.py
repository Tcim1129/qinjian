"""add behavior summary to profile snapshots

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_profile_snapshots" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("relationship_profile_snapshots")
    }
    if "behavior_summary" not in columns:
        op.add_column(
            "relationship_profile_snapshots",
            sa.Column("behavior_summary", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "relationship_profile_snapshots" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("relationship_profile_snapshots")
    }
    if "behavior_summary" in columns:
        op.drop_column("relationship_profile_snapshots", "behavior_summary")

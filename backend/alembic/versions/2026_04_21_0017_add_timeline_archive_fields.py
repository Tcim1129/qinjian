"""add timeline archive fields

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "checkins" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("checkins")}

    if "archive_title" not in columns:
        op.add_column(
            "checkins",
            sa.Column("archive_title", sa.String(length=120), nullable=True),
        )
    if "archive_summary" not in columns:
        op.add_column(
            "checkins",
            sa.Column("archive_summary", sa.Text(), nullable=True),
        )
    if "archive_tags" not in columns:
        op.add_column(
            "checkins",
            sa.Column("archive_tags", sa.JSON(), nullable=True),
        )
    if "raw_retention_until" not in columns:
        op.add_column(
            "checkins",
            sa.Column("raw_retention_until", sa.DateTime(), nullable=True),
        )
    if "raw_deleted_at" not in columns:
        op.add_column(
            "checkins",
            sa.Column("raw_deleted_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "checkins" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("checkins")}

    if "raw_deleted_at" in columns:
        op.drop_column("checkins", "raw_deleted_at")
    if "raw_retention_until" in columns:
        op.drop_column("checkins", "raw_retention_until")
    if "archive_tags" in columns:
        op.drop_column("checkins", "archive_tags")
    if "archive_summary" in columns:
        op.drop_column("checkins", "archive_summary")
    if "archive_title" in columns:
        op.drop_column("checkins", "archive_title")

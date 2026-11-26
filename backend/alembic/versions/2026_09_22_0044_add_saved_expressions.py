"""Add owner-only saved expressions, without importing an old worktree's migrations.

Revision ID: 0044
Revises: 0043
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0044'
down_revision: Union[str, None] = '0043'
branch_labels = None
depends_on = None


def upgrade():
    identifier = sa.CHAR(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")
    op.create_table(
        "saved_expressions",
        sa.Column("id", identifier, primary_key=True),
        sa.Column("user_id", identifier, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pair_id", identifier, sa.ForeignKey("pairs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_saved_expressions_owner_scope", "saved_expressions", ["user_id", "pair_id", "created_at"])


def downgrade():
    op.drop_index("ix_saved_expressions_owner_scope", table_name="saved_expressions")
    op.drop_table("saved_expressions")

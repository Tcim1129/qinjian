"""add upload asset ownership table

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "upload_assets" in set(inspector.get_table_names()):
        return

    op.create_table(
        "upload_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("subdir", sa.String(length=40), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(
        op.f("ix_upload_assets_storage_path"),
        "upload_assets",
        ["storage_path"],
        unique=True,
    )
    op.create_index(op.f("ix_upload_assets_subdir"), "upload_assets", ["subdir"])
    op.create_index(
        op.f("ix_upload_assets_owner_user_id"),
        "upload_assets",
        ["owner_user_id"],
    )
    op.create_index(op.f("ix_upload_assets_pair_id"), "upload_assets", ["pair_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "upload_assets" not in set(inspector.get_table_names()):
        return

    op.drop_index(op.f("ix_upload_assets_pair_id"), table_name="upload_assets")
    op.drop_index(op.f("ix_upload_assets_owner_user_id"), table_name="upload_assets")
    op.drop_index(op.f("ix_upload_assets_subdir"), table_name="upload_assets")
    op.drop_index(op.f("ix_upload_assets_storage_path"), table_name="upload_assets")
    op.drop_table("upload_assets")

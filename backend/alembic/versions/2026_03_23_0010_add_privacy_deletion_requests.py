"""add privacy deletion requests

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "privacy_deletion_requests" not in existing_tables:
        op.create_table(
            "privacy_deletion_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("requested_at", sa.DateTime(), nullable=False),
            sa.Column("scheduled_for", sa.DateTime(), nullable=False),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {
        index["name"] for index in inspector.get_indexes("privacy_deletion_requests")
    }
    if op.f("ix_privacy_deletion_requests_user_id") not in indexes:
        op.create_index(
            op.f("ix_privacy_deletion_requests_user_id"),
            "privacy_deletion_requests",
            ["user_id"],
            unique=False,
        )
    if op.f("ix_privacy_deletion_requests_status") not in indexes:
        op.create_index(
            op.f("ix_privacy_deletion_requests_status"),
            "privacy_deletion_requests",
            ["status"],
            unique=False,
        )
    if op.f("ix_privacy_deletion_requests_requested_at") not in indexes:
        op.create_index(
            op.f("ix_privacy_deletion_requests_requested_at"),
            "privacy_deletion_requests",
            ["requested_at"],
            unique=False,
        )
    if op.f("ix_privacy_deletion_requests_scheduled_for") not in indexes:
        op.create_index(
            op.f("ix_privacy_deletion_requests_scheduled_for"),
            "privacy_deletion_requests",
            ["scheduled_for"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_privacy_deletion_requests_scheduled_for"),
        table_name="privacy_deletion_requests",
    )
    op.drop_index(
        op.f("ix_privacy_deletion_requests_requested_at"),
        table_name="privacy_deletion_requests",
    )
    op.drop_index(
        op.f("ix_privacy_deletion_requests_status"),
        table_name="privacy_deletion_requests",
    )
    op.drop_index(
        op.f("ix_privacy_deletion_requests_user_id"),
        table_name="privacy_deletion_requests",
    )
    op.drop_table("privacy_deletion_requests")

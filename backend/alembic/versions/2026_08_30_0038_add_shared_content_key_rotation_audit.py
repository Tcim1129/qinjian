"""Add shared-content key rotation audit timestamp.

Revision ID: 0038
Revises: 0037
"""

from alembic import op
import sqlalchemy as sa


revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_authorized_shared_contents",
        sa.Column("key_rotated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emotimirror_authorized_shared_contents", "key_rotated_at")

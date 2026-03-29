"""add product prefs and client context

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "product_prefs" not in user_columns:
        op.add_column("users", sa.Column("product_prefs", sa.JSON(), nullable=True))

    checkin_columns = {column["name"] for column in inspector.get_columns("checkins")}
    if "client_context" not in checkin_columns:
        op.add_column(
            "checkins",
            sa.Column("client_context", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("checkins", "client_context")
    op.drop_column("users", "product_prefs")


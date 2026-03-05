"""add custom partner nickname fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # pairs: add custom partner nickname fields
    if "pairs" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("pairs")]
        if "custom_partner_nickname_a" not in cols:
            op.add_column(
                "pairs",
                sa.Column("custom_partner_nickname_a", sa.String(50), nullable=True),
            )
        if "custom_partner_nickname_b" not in cols:
            op.add_column(
                "pairs",
                sa.Column("custom_partner_nickname_b", sa.String(50), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "pairs" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("pairs")]
        if "custom_partner_nickname_b" in cols:
            op.drop_column("pairs", "custom_partner_nickname_b")
        if "custom_partner_nickname_a" in cols:
            op.drop_column("pairs", "custom_partner_nickname_a")

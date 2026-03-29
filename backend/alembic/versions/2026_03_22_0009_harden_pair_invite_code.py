"""widen pair invite code length

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "pairs" not in inspector.get_table_names():
        return

    columns = {column["name"]: column for column in inspector.get_columns("pairs")}
    invite_code_column = columns.get("invite_code")
    invite_code_type = invite_code_column.get("type") if invite_code_column else None
    current_length = getattr(invite_code_type, "length", None)
    if current_length == 12:
        return

    op.alter_column(
        "pairs",
        "invite_code",
        existing_type=sa.String(length=current_length or 6),
        type_=sa.String(length=12),
        existing_nullable=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "pairs" not in inspector.get_table_names():
        return

    columns = {column["name"]: column for column in inspector.get_columns("pairs")}
    invite_code_column = columns.get("invite_code")
    invite_code_type = invite_code_column.get("type") if invite_code_column else None
    current_length = getattr(invite_code_type, "length", None)
    if current_length == 6:
        return

    op.alter_column(
        "pairs",
        "invite_code",
        existing_type=sa.String(length=current_length or 12),
        type_=sa.String(length=6),
        existing_nullable=False,
    )

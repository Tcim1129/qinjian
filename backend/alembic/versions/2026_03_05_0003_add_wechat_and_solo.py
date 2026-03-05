"""add wechat fields and solo mode support

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # users: add wechat fields
    if "users" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("users")]
        if "phone" not in cols:
            op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
            op.create_index("ix_users_phone", "users", ["phone"], unique=True)
        if "wechat_openid" not in cols:
            op.add_column(
                "users", sa.Column("wechat_openid", sa.String(64), nullable=True)
            )
            op.create_index(
                "ix_users_wechat_openid", "users", ["wechat_openid"], unique=True
            )
        if "wechat_unionid" not in cols:
            op.add_column(
                "users", sa.Column("wechat_unionid", sa.String(64), nullable=True)
            )
        if "wechat_avatar" not in cols:
            op.add_column(
                "users", sa.Column("wechat_avatar", sa.String(500), nullable=True)
            )

    # checkins: pair_id nullable for solo
    if "checkins" in inspector.get_table_names():
        op.alter_column(
            "checkins",
            "pair_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )

    # reports: pair_id nullable and add user_id
    if "reports" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("reports")]
        if "user_id" not in cols:
            op.add_column(
                "reports",
                sa.Column(
                    "user_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("users.id"),
                    nullable=True,
                ),
            )
        op.alter_column(
            "reports",
            "pair_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade() -> None:
    # reverse order
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "reports" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("reports")]
        if "user_id" in cols:
            op.drop_constraint("reports_user_id_fkey", "reports", type_="foreignkey")
            op.drop_column("reports", "user_id")
        op.alter_column(
            "reports",
            "pair_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )

    if "checkins" in inspector.get_table_names():
        op.alter_column(
            "checkins",
            "pair_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )

    if "users" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("users")]
        if "wechat_avatar" in cols:
            op.drop_column("users", "wechat_avatar")
        if "wechat_unionid" in cols:
            op.drop_column("users", "wechat_unionid")
        if "wechat_openid" in cols:
            op.drop_index("ix_users_wechat_openid", table_name="users")
            op.drop_column("users", "wechat_openid")
        if "phone" in cols:
            op.drop_index("ix_users_phone", table_name="users")
            op.drop_column("users", "phone")

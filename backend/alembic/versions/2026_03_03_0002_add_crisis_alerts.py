"""add crisis_alerts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "crisis_alerts" not in existing_tables:
        op.create_table(
            "crisis_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("reports.id"),
                nullable=True,
            ),
            sa.Column(
                "level",
                sa.Enum("none", "mild", "moderate", "severe", name="crisislevel"),
                nullable=False,
                server_default="none",
            ),
            sa.Column(
                "previous_level",
                sa.Enum(
                    "none",
                    "mild",
                    "moderate",
                    "severe",
                    name="crisislevel",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column(
                "status",
                sa.Enum(
                    "active",
                    "acknowledged",
                    "resolved",
                    "escalated",
                    name="crisisalertstatus",
                ),
                nullable=False,
                server_default="active",
            ),
            sa.Column("intervention_type", sa.String(30), nullable=True),
            sa.Column("intervention_title", sa.String(100), nullable=True),
            sa.Column("intervention_desc", sa.Text, nullable=True),
            sa.Column("action_items", sa.JSON, nullable=True),
            sa.Column("health_score", sa.Float, nullable=True),
            sa.Column(
                "acknowledged_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("acknowledged_at", sa.DateTime, nullable=True),
            sa.Column("resolved_at", sa.DateTime, nullable=True),
            sa.Column("resolve_note", sa.Text, nullable=True),
            sa.Column(
                "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
            ),
        )


def downgrade() -> None:
    op.drop_table("crisis_alerts")
    # 清理枚举类型（如果没有其他表使用）
    op.execute("DROP TYPE IF EXISTS crisisalertstatus")
    # crisislevel 保留，因为可能其他地方会用

"""initial schema - all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """如果表已存在则跳过（兼容 create_all 已创建的情况）"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # ── users ──
    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
            sa.Column("nickname", sa.String(50), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("avatar_url", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── pairs ──
    if "pairs" not in existing_tables:
        # 创建枚举类型
        pairtype = postgresql.ENUM(
            "couple",
            "spouse",
            "bestfriend",
            "parent",
            name="pairtype",
            create_type=False,
        )
        pairstatus = postgresql.ENUM(
            "pending", "active", "ended", name="pairstatus", create_type=False
        )
        op.execute(
            "CREATE TYPE pairtype AS ENUM ('couple', 'spouse', 'bestfriend', 'parent')"
        )
        op.execute("CREATE TYPE pairstatus AS ENUM ('pending', 'active', 'ended')")

        op.create_table(
            "pairs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_a_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "user_b_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("type", pairtype, nullable=False),
            sa.Column("status", pairstatus, nullable=False),
            sa.Column(
                "invite_code", sa.String(6), unique=True, index=True, nullable=False
            ),
            sa.Column(
                "unbind_requested_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("unbind_requested_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("attachment_style_a", sa.String(20), nullable=True),
            sa.Column("attachment_style_b", sa.String(20), nullable=True),
            sa.Column("attachment_analyzed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "is_long_distance", sa.Boolean(), nullable=True, server_default="false"
            ),
        )
    else:
        # 表已存在，检查并添加缺失的列
        existing_columns = [c["name"] for c in inspector.get_columns("pairs")]
        if "unbind_requested_by" not in existing_columns:
            op.add_column(
                "pairs",
                sa.Column(
                    "unbind_requested_by", postgresql.UUID(as_uuid=True), nullable=True
                ),
            )
        if "unbind_requested_at" not in existing_columns:
            op.add_column(
                "pairs", sa.Column("unbind_requested_at", sa.DateTime(), nullable=True)
            )
        if "attachment_style_a" not in existing_columns:
            op.add_column(
                "pairs", sa.Column("attachment_style_a", sa.String(20), nullable=True)
            )
        if "attachment_style_b" not in existing_columns:
            op.add_column(
                "pairs", sa.Column("attachment_style_b", sa.String(20), nullable=True)
            )
        if "attachment_analyzed_at" not in existing_columns:
            op.add_column(
                "pairs",
                sa.Column("attachment_analyzed_at", sa.DateTime(), nullable=True),
            )
        if "is_long_distance" not in existing_columns:
            op.add_column(
                "pairs",
                sa.Column(
                    "is_long_distance",
                    sa.Boolean(),
                    nullable=True,
                    server_default="false",
                ),
            )

    # ── checkins ──
    if "checkins" not in existing_tables:
        op.create_table(
            "checkins",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("voice_url", sa.String(500), nullable=True),
            sa.Column("mood_tags", postgresql.JSON(), nullable=True),
            sa.Column("sentiment_score", sa.Float(), nullable=True),
            sa.Column("mood_score", sa.Integer(), nullable=True),
            sa.Column("interaction_freq", sa.Integer(), nullable=True),
            sa.Column("interaction_initiative", sa.String(10), nullable=True),
            sa.Column("deep_conversation", sa.Boolean(), nullable=True),
            sa.Column("task_completed", sa.Boolean(), nullable=True),
            sa.Column("checkin_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    else:
        existing_columns = [c["name"] for c in inspector.get_columns("checkins")]
        for col_name, col_type in [
            ("mood_score", sa.Integer()),
            ("interaction_freq", sa.Integer()),
            ("interaction_initiative", sa.String(10)),
            ("deep_conversation", sa.Boolean()),
            ("task_completed", sa.Boolean()),
        ]:
            if col_name not in existing_columns:
                op.add_column("checkins", sa.Column(col_name, col_type, nullable=True))

    # ── reports ──
    if "reports" not in existing_tables:
        reporttype = postgresql.ENUM(
            "daily", "weekly", "monthly", "solo", name="reporttype", create_type=False
        )
        reportstatus = postgresql.ENUM(
            "pending", "completed", "failed", name="reportstatus", create_type=False
        )
        op.execute(
            "DO $$ BEGIN CREATE TYPE reporttype AS ENUM ('daily', 'weekly', 'monthly', 'solo'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
        op.execute(
            "DO $$ BEGIN CREATE TYPE reportstatus AS ENUM ('pending', 'completed', 'failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )

        op.create_table(
            "reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
            ),
            sa.Column("type", reporttype, nullable=False),
            sa.Column("status", reportstatus, nullable=False),
            sa.Column("content", postgresql.JSON(), nullable=True),
            sa.Column("health_score", sa.Float(), nullable=True),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── relationship_trees ──
    if "relationship_trees" not in existing_tables:
        op.execute(
            "DO $$ BEGIN CREATE TYPE treelevel AS ENUM ('seed', 'sprout', 'sapling', 'tree', 'big_tree', 'forest'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
        treelevel = postgresql.ENUM(
            "seed",
            "sprout",
            "sapling",
            "tree",
            "big_tree",
            "forest",
            name="treelevel",
            create_type=False,
        )

        op.create_table(
            "relationship_trees",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                unique=True,
                nullable=False,
            ),
            sa.Column(
                "growth_points", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("level", treelevel, nullable=False),
            sa.Column("milestones", postgresql.JSON(), nullable=True),
            sa.Column("last_watered", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── relationship_tasks ──
    if "relationship_tasks" not in existing_tables:
        op.execute(
            "DO $$ BEGIN CREATE TYPE taskstatus AS ENUM ('pending', 'completed', 'skipped'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
        taskstatus = postgresql.ENUM(
            "pending", "completed", "skipped", name="taskstatus", create_type=False
        )

        op.create_table(
            "relationship_tasks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("title", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("category", sa.String(30), server_default="activity"),
            sa.Column("status", taskstatus, nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── long_distance_activities ──
    if "long_distance_activities" not in existing_tables:
        op.create_table(
            "long_distance_activities",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
            ),
            sa.Column("type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── milestones ──
    if "milestones" not in existing_tables:
        op.create_table(
            "milestones",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "pair_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pairs.id"),
                nullable=False,
            ),
            sa.Column("type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(100), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "reminder_sent", sa.Boolean(), nullable=True, server_default="false"
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── community_tips ──
    if "community_tips" not in existing_tables:
        op.create_table(
            "community_tips",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("target_pair_type", sa.String(20), server_default="couple"),
            sa.Column("title", sa.String(100), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "ai_generated", sa.Boolean(), nullable=True, server_default="false"
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # ── user_notifications ──
    if "user_notifications" not in existing_tables:
        op.create_table(
            "user_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("type", sa.String(30), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("user_notifications")
    op.drop_table("community_tips")
    op.drop_table("milestones")
    op.drop_table("long_distance_activities")
    op.drop_table("relationship_tasks")
    op.drop_table("relationship_trees")
    op.drop_table("reports")
    op.drop_table("checkins")
    op.drop_table("pairs")
    op.drop_table("users")

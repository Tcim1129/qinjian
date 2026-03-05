"""数据模型 - SQLAlchemy ORM"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Text, ForeignKey, Date, Enum, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# ── 枚举 ──


class PairType(str, PyEnum):
    COUPLE = "couple"  # 情侣
    SPOUSE = "spouse"  # 夫妻
    BESTFRIEND = "bestfriend"  # 挚友
    PARENT = "parent"  # 夫妻（育儿阶段）


class PairStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class ReportType(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SOLO = "solo"  # 单方打卡的个人情感日记


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CrisisLevel(str, PyEnum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class CrisisAlertStatus(str, PyEnum):
    ACTIVE = "active"  # 当前生效
    ACKNOWLEDGED = "acknowledged"  # 用户已确认查看
    RESOLVED = "resolved"  # 已解决/降级
    ESCALATED = "escalated"  # 已升级至专业帮助


# ── 模型 ──


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )
    nickname: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wechat_openid: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    wechat_unionid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    wechat_avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    checkins: Mapped[list["Checkin"]] = relationship(back_populates="user")


class Pair(Base):
    __tablename__ = "pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    user_b_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    type: Mapped[PairType] = mapped_column(Enum(PairType))
    status: Mapped[PairStatus] = mapped_column(
        Enum(PairStatus), default=PairStatus.PENDING
    )
    invite_code: Mapped[str] = mapped_column(
        String(6), unique=True, index=True
    )  # 6位数字绑定码
    # ── 解绑字段 ──
    unbind_requested_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    unbind_requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # ── 依恋类型（Phase 4 新增）──
    attachment_style_a: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attachment_style_b: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attachment_analyzed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # ── 异地标记（Phase 4 新增）──
    is_long_distance: Mapped[bool | None] = mapped_column(default=False, nullable=True)

    # 关系
    checkins: Mapped[list["Checkin"]] = relationship(back_populates="pair")
    reports: Mapped[list["Report"]] = relationship(back_populates="pair")


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)  # 打卡文字内容
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mood_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 结构化四步打卡字段 ──
    mood_score: Mapped[int | None] = mapped_column(nullable=True)
    interaction_freq: Mapped[int | None] = mapped_column(nullable=True)
    interaction_initiative: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    deep_conversation: Mapped[bool | None] = mapped_column(nullable=True)
    task_completed: Mapped[bool | None] = mapped_column(nullable=True)

    checkin_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="checkins")
    pair: Mapped["Pair"] = relationship(back_populates="checkins")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    type: Mapped[ReportType] = mapped_column(Enum(ReportType))
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.COMPLETED
    )
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    pair: Mapped["Pair"] = relationship(back_populates="reports")


# ── 关系树（游戏化） ──


class TreeLevel(str, PyEnum):
    SEED = "seed"
    SPROUT = "sprout"
    SAPLING = "sapling"
    TREE = "tree"
    BIG_TREE = "big_tree"
    FOREST = "forest"


TREE_LEVEL_THRESHOLDS = [
    (0, TreeLevel.SEED),
    (50, TreeLevel.SPROUT),
    (150, TreeLevel.SAPLING),
    (350, TreeLevel.TREE),
    (700, TreeLevel.BIG_TREE),
    (1200, TreeLevel.FOREST),
]


def calc_tree_level(points: int) -> TreeLevel:
    """根据成长值计算等级"""
    level = TreeLevel.SEED
    for threshold, lvl in TREE_LEVEL_THRESHOLDS:
        if points >= threshold:
            level = lvl
    return level


class RelationshipTree(Base):
    __tablename__ = "relationship_trees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"), unique=True)
    growth_points: Mapped[int] = mapped_column(default=0)
    level: Mapped[TreeLevel] = mapped_column(Enum(TreeLevel), default=TreeLevel.SEED)
    milestones: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=lambda: []
    )
    last_watered: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    pair: Mapped["Pair"] = relationship()


# ── 关系任务（Phase 4：依恋模式适配） ──


class RelationshipTask(Base):
    __tablename__ = "relationship_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )  # None = 双方共同任务
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(30), default="activity")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING
    )
    due_date: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# ── 异地互动活动（Phase 4：场景延伸） ──


class LongDistanceActivity(Base):
    __tablename__ = "long_distance_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    type: Mapped[str] = mapped_column(String(30))  # movie/meal/chat/gift/exercise
    title: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# ── 关系里程碑（Phase 4：关键节点服务） ──


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date)
    reminder_sent: Mapped[bool | None] = mapped_column(default=False, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# ── 社群技巧（Phase 4：体验升级） ──


class CommunityTip(Base):
    __tablename__ = "community_tips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    target_pair_type: Mapped[str] = mapped_column(String(20), default="couple")
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    ai_generated: Mapped[bool | None] = mapped_column(default=False, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# ── 用户通知（Phase 4：体验升级） ──


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(30))  # crisis/task/tip/milestone
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool | None] = mapped_column(default=False, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# ── 危机预警记录（Crisis Level Grading System） ──


class CrisisAlert(Base):
    __tablename__ = "crisis_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id"), nullable=True
    )  # 触发此预警的报告
    level: Mapped[CrisisLevel] = mapped_column(
        Enum(CrisisLevel), default=CrisisLevel.NONE
    )
    previous_level: Mapped[CrisisLevel | None] = mapped_column(
        Enum(CrisisLevel), nullable=True
    )  # 上一次的等级，用于趋势对比
    status: Mapped[CrisisAlertStatus] = mapped_column(
        Enum(CrisisAlertStatus), default=CrisisAlertStatus.ACTIVE
    )
    # 干预方案（从 AI 报告中提取）
    intervention_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    intervention_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    intervention_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 健康分数快照
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 用户操作记录
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolve_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    pair: Mapped["Pair"] = relationship()
    report: Mapped["Report"] = relationship()

"""数据模型 - SQLAlchemy ORM"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Text, ForeignKey, Date, Enum, Float, JSON, Integer
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


def enum_values(enum_cls: type[PyEnum]) -> Enum:
    return Enum(
        enum_cls,
        values_callable=lambda enum_items: [item.value for item in enum_items],
        validate_strings=True,
        native_enum=True,
        name=enum_cls.__name__.lower(),
    )


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
    product_prefs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
    type: Mapped[PairType] = mapped_column(enum_values(PairType))
    status: Mapped[PairStatus] = mapped_column(
        enum_values(PairStatus), default=PairStatus.PENDING
    )
    invite_code: Mapped[str] = mapped_column(
        String(12), unique=True, index=True
    )  # 高熵邀请码，降低枚举撞库风险
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

    # ── 自定义伴侣昵称（给伴侣设置备注名）──
    custom_partner_nickname_a: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    custom_partner_nickname_b: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

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
    client_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
    type: Mapped[ReportType] = mapped_column(enum_values(ReportType))
    status: Mapped[ReportStatus] = mapped_column(
        enum_values(ReportStatus), default=ReportStatus.COMPLETED
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
    level: Mapped[TreeLevel] = mapped_column(
        enum_values(TreeLevel), default=TreeLevel.SEED
    )
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
        enum_values(TaskStatus), default=TaskStatus.PENDING
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
        enum_values(CrisisLevel), default=CrisisLevel.NONE
    )
    previous_level: Mapped[CrisisLevel | None] = mapped_column(
        enum_values(CrisisLevel), nullable=True
    )  # 上一次的等级，用于趋势对比
    status: Mapped[CrisisAlertStatus] = mapped_column(
        enum_values(CrisisAlertStatus), default=CrisisAlertStatus.ACTIVE
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


# ── AI Agent 聊天会话存储 (Phase 5：陪伴打卡升级) ──


class AgentChatSession(Base):
    __tablename__ = "agent_chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    # 此会话的状态（例如：active, archived）
    status: Mapped[str] = mapped_column(String(20), default="active")
    # 今日会话是否已成功触发打卡生成提取
    has_extracted_checkin: Mapped[bool] = mapped_column(default=False)
    # 本次会话相关日期（归档用）
    session_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    user: Mapped["User"] = relationship()
    pair: Mapped["Pair"] = relationship()
    messages: Mapped[list["AgentChatMessage"]] = relationship(
        back_populates="session",
        order_by="asc(AgentChatMessage.created_at)"
    )


class AgentChatMessage(Base):
    __tablename__ = "agent_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_chat_sessions.id"), index=True)
    # 角色 (user, assistant, system, tool)
    role: Mapped[str] = mapped_column(String(20))
    # 消息正文
    content: Mapped[str] = mapped_column(Text)
    # 若为 tool_calls/function_call，将字典存入 payload
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # 关系
    session: Mapped["AgentChatSession"] = relationship(back_populates="messages")


# ── 关系智能层（Relationship Intelligence Layer） ──


class RelationshipEvent(Base):
    __tablename__ = "relationship_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="system")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    pair: Mapped["Pair"] = relationship()
    user: Mapped["User"] = relationship()


class RelationshipProfileSnapshot(Base):
    __tablename__ = "relationship_profile_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    window_days: Mapped[int] = mapped_column(index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attachment_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggested_focus: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_from_event_at: Mapped[datetime | None] = mapped_column(nullable=True)
    version: Mapped[str] = mapped_column(String(30), default="v1")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    pair: Mapped["Pair"] = relationship()
    user: Mapped["User"] = relationship()


class InterventionPlan(Base):
    __tablename__ = "intervention_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    plan_type: Mapped[str] = mapped_column(String(50), index=True)
    trigger_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("relationship_events.id"), nullable=True
    )
    trigger_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("relationship_profile_snapshots.id"), nullable=True
    )
    risk_level: Mapped[str] = mapped_column(String(20), default="none")
    goal_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_version: Mapped[str] = mapped_column(String(30), default="v1")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    pair: Mapped["Pair"] = relationship()
    user: Mapped["User"] = relationship()
    trigger_event: Mapped["RelationshipEvent"] = relationship(
        foreign_keys=[trigger_event_id]
    )
    trigger_snapshot: Mapped["RelationshipProfileSnapshot"] = relationship(
        foreign_keys=[trigger_snapshot_id]
    )


class PlaybookRun(Base):
    __tablename__ = "playbook_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intervention_plans.id"), unique=True
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    plan_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    current_day: Mapped[int] = mapped_column(default=1)
    active_branch: Mapped[str] = mapped_column(String(30), default="steady", index=True)
    branch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch_started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_viewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    transition_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    plan: Mapped["InterventionPlan"] = relationship()
    pair: Mapped["Pair"] = relationship()
    user: Mapped["User"] = relationship()
    transitions: Mapped[list["PlaybookTransition"]] = relationship(
        back_populates="run",
        order_by="asc(PlaybookTransition.created_at)",
    )


class PlaybookTransition(Base):
    __tablename__ = "playbook_transitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playbook_runs.id"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intervention_plans.id"), index=True
    )
    pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pairs.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    transition_type: Mapped[str] = mapped_column(String(40), default="initialized")
    trigger_type: Mapped[str] = mapped_column(String(40), default="run_started")
    trigger_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_day: Mapped[int | None] = mapped_column(nullable=True)
    to_day: Mapped[int] = mapped_column(default=1)
    from_branch: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_branch: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    run: Mapped["PlaybookRun"] = relationship(back_populates="transitions")
    plan: Mapped["InterventionPlan"] = relationship()
    pair: Mapped["Pair"] = relationship()
    user: Mapped["User"] = relationship()


class InterventionPolicyLibrary(Base):
    __tablename__ = "intervention_policy_library"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )
    plan_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    branch: Mapped[str] = mapped_column(String(30), index=True)
    branch_label: Mapped[str] = mapped_column(String(50))
    intensity: Mapped[str] = mapped_column(String(20), index=True)
    intensity_label: Mapped[str] = mapped_column(String(50))
    copy_mode: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    copy_mode_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    when_to_use: Mapped[str] = mapped_column(Text)
    success_marker: Mapped[str] = mapped_column(Text)
    guardrail: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="v1")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    source: Mapped[str] = mapped_column(String(20), default="seed")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class PrivacyDeletionRequest(Base):
    __tablename__ = "privacy_deletion_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    requested_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewed_by])

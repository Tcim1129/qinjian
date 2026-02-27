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
    COUPLE = "couple"       # 情侣
    SPOUSE = "spouse"       # 夫妻
    BESTFRIEND = "bestfriend"  # 挚友


class PairStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class ReportType(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SOLO = "solo"        # 单方打卡的个人情感日记


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# ── 模型 ──

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 关系
    checkins: Mapped[list["Checkin"]] = relationship(back_populates="user")


class Pair(Base):
    __tablename__ = "pairs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    user_b_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[PairType] = mapped_column(Enum(PairType))
    status: Mapped[PairStatus] = mapped_column(Enum(PairStatus), default=PairStatus.PENDING)
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 关系
    checkins: Mapped[list["Checkin"]] = relationship(back_populates="pair")
    reports: Mapped[list["Report"]] = relationship(back_populates="pair")


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)  # 打卡文字内容
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 图片URL
    voice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 语音URL
    mood_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 情绪标签
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkin_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 关系
    user: Mapped["User"] = relationship(back_populates="checkins")
    pair: Mapped["Pair"] = relationship(back_populates="checkins")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    type: Mapped[ReportType] = mapped_column(Enum(ReportType))
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.COMPLETED)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # AI生成的报告JSON，可能为空
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 关系
    pair: Mapped["Pair"] = relationship(back_populates="reports")


# ── 关系树（游戏化） ──

class TreeLevel(str, PyEnum):
    SEED = "seed"           # 种子  0-49
    SPROUT = "sprout"       # 嫩芽  50-149
    SAPLING = "sapling"     # 树苗  150-349
    TREE = "tree"           # 小树  350-699
    BLOSSOM = "blossom"     # 花开  700+


TREE_LEVEL_THRESHOLDS = [
    (0, TreeLevel.SEED),
    (50, TreeLevel.SPROUT),
    (150, TreeLevel.SAPLING),
    (350, TreeLevel.TREE),
    (700, TreeLevel.BLOSSOM),
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"), unique=True)
    growth_points: Mapped[int] = mapped_column(default=0)
    level: Mapped[TreeLevel] = mapped_column(Enum(TreeLevel), default=TreeLevel.SEED)
    milestones: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: [])
    last_watered: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 关系
    pair: Mapped["Pair"] = relationship()

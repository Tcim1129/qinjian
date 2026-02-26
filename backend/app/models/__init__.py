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


# ── 模型 ──

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # 关系
    user: Mapped["User"] = relationship(back_populates="checkins")
    pair: Mapped["Pair"] = relationship(back_populates="checkins")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pairs.id"))
    type: Mapped[ReportType] = mapped_column(Enum(ReportType))
    content: Mapped[dict] = mapped_column(JSON)  # AI生成的报告JSON
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # 关系
    pair: Mapped["Pair"] = relationship(back_populates="reports")

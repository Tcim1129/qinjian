"""Pydantic 请求/响应模型"""

import uuid
from datetime import date, datetime
from pydantic import BaseModel


# ── 认证 ──


class RegisterRequest(BaseModel):
    email: str
    nickname: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── 用户 ──


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    nickname: str
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 配对 ──


class PairCreateRequest(BaseModel):
    type: str  # couple / spouse / bestfriend


class PairJoinRequest(BaseModel):
    invite_code: str


class PairResponse(BaseModel):
    id: uuid.UUID
    user_a_id: uuid.UUID
    user_b_id: uuid.UUID | None
    type: str
    status: str
    invite_code: str
    unbind_requested_by: uuid.UUID | None = None
    unbind_requested_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 打卡 ──


class CheckinRequest(BaseModel):
    pair_id: uuid.UUID
    content: str
    mood_tags: list[str] | None = None
    image_url: str | None = None
    voice_url: str | None = None
    # 结构化四步打卡（计划书§4.1.2 表9）
    mood_score: int | None = None  # 1-4
    interaction_freq: int | None = None  # 0-10+
    interaction_initiative: str | None = None  # "me"/"partner"/"equal"
    deep_conversation: bool | None = None
    task_completed: bool | None = None


class CheckinResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    image_url: str | None = None
    voice_url: str | None = None
    mood_tags: dict | None = None
    sentiment_score: float | None = None
    mood_score: int | None = None
    interaction_freq: int | None = None
    interaction_initiative: str | None = None
    deep_conversation: bool | None = None
    task_completed: bool | None = None
    checkin_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 报告 ──


class ReportResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    type: str
    status: str
    content: dict | None = None
    health_score: float | None = None
    report_date: date
    created_at: datetime

    model_config = {"from_attributes": True}

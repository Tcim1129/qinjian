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


class WechatLoginRequest(BaseModel):
    code: str
    nickname: str | None = None
    avatar_url: str | None = None
    unionid: str | None = None


class PhoneSendCodeRequest(BaseModel):
    phone: str


class PhoneLoginRequest(BaseModel):
    phone: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── 用户 ──


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None = None
    nickname: str
    avatar_url: str | None = None
    wechat_openid: str | None = None
    wechat_unionid: str | None = None
    wechat_avatar: str | None = None
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
    partner_id: uuid.UUID | None = None
    partner_nickname: str | None = None
    partner_avatar: str | None = None
    partner_email: str | None = None
    partner_phone: str | None = None
    custom_partner_nickname: str | None = None  # 我给伴侣设置的备注名

    model_config = {"from_attributes": True}


class UpdatePartnerNicknameRequest(BaseModel):
    custom_nickname: str


# ── 打卡 ──


class CheckinRequest(BaseModel):
    pair_id: uuid.UUID | None = None
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
    pair_id: uuid.UUID | None = None
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
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    type: str
    status: str
    content: dict | None = None
    health_score: float | None = None
    report_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 关系任务 ──


class TaskResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    user_id: uuid.UUID | None = None
    title: str
    description: str
    category: str
    status: str
    due_date: date
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 依恋类型 ──


class AttachmentStyleResponse(BaseModel):
    type: str
    label: str
    confidence: float | None = None
    analysis: str | None = None
    growth_suggestion: str | None = None


# ── 危机预警 ──


class InterventionSchema(BaseModel):
    type: str  # none/fun_activity/communication_guide/professional_help
    title: str | None = None
    description: str | None = None
    action_items: list[str] | None = None


class CrisisAlertResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    report_id: uuid.UUID | None = None
    level: str  # none/mild/moderate/severe
    previous_level: str | None = None
    status: str  # active/acknowledged/resolved/escalated
    intervention_type: str | None = None
    intervention_title: str | None = None
    intervention_desc: str | None = None
    action_items: list | None = None
    health_score: float | None = None
    acknowledged_by: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolve_note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrisisStatusResponse(BaseModel):
    """当前危机状态（兼容旧 API + 新 CrisisAlert）"""

    crisis_level: str
    alert_id: uuid.UUID | None = None
    alert_status: str | None = None
    intervention: InterventionSchema | None = None
    health_score: float | None = None
    source_report_id: str | None = None
    source_report_type: str | None = None
    report_date: str | None = None
    previous_level: str | None = None
    message: str | None = None


class CrisisHistoryItemSchema(BaseModel):
    date: str
    type: str | None = None
    crisis_level: str
    health_score: float | None = None
    intervention_type: str | None = None
    alert_status: str | None = None


class CrisisHistoryResponse(BaseModel):
    pair_id: str
    history: list[CrisisHistoryItemSchema]


class CrisisAcknowledgeRequest(BaseModel):
    """用户确认已查看预警"""

    pass


class CrisisResolveRequest(BaseModel):
    """用户标记预警已解决"""

    note: str | None = None


class CrisisEscalateRequest(BaseModel):
    """升级至专业帮助"""

    reason: str | None = None

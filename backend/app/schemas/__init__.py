"""Pydantic 请求/响应模型"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.invite_codes import (
    INVITE_CODE_LENGTH,
    INVITE_CODE_PATTERN,
    normalize_invite_code,
)
from app.services.upload_access import to_client_upload_url


class RequestModel(BaseModel):
    model_config = {"extra": "forbid"}


# ── 认证 ──


class RegisterRequest(RequestModel):
    account: str | None = Field(default=None, description="邮箱或手机号")
    email: str | None = Field(default=None, description="兼容旧版邮箱字段")
    nickname: str
    password: str


class LoginRequest(RequestModel):
    account: str | None = Field(default=None, description="邮箱或手机号")
    email: str | None = Field(default=None, description="兼容旧版邮箱字段")
    password: str


class WechatLoginRequest(RequestModel):
    code: str
    nickname: str | None = None
    avatar_url: str | None = None
    unionid: str | None = None


class PhoneSendCodeRequest(RequestModel):
    phone: str


class PhoneLoginRequest(RequestModel):
    phone: str
    code: str


class PasswordResetByPhoneRequest(RequestModel):
    phone: str
    code: str
    new_password: str


class ProfileUpdateCodeSendRequest(RequestModel):
    field: Literal["email", "phone"]
    value: str = Field(min_length=1, max_length=120)


class ProfileUpdateCodeConfirmRequest(RequestModel):
    field: Literal["email", "phone"]
    value: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── 用户 ──


class AvatarPresentation(BaseModel):
    focus_x: float = Field(default=50.0, ge=0.0, le=100.0)
    focus_y: float = Field(default=50.0, ge=0.0, le=100.0)
    scale: float = Field(default=1.0, ge=1.0, le=3.0)


class TaskPlannerDefaultsResponse(BaseModel):
    daily_ai_task_count: int = Field(ge=3, le=8)
    reminder_enabled: bool = True
    reminder_time: str
    reminder_timezone: str


class TaskPlannerDefaultsUpdateRequest(RequestModel):
    daily_ai_task_count: int | None = Field(default=None, ge=3, le=8)
    reminder_enabled: bool | None = None
    reminder_time: str | None = None
    reminder_timezone: str | None = Field(default=None, max_length=80)

    @field_validator("reminder_time")
    @classmethod
    def _validate_reminder_time(cls, value: str | None):
        if value is None:
            return value
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value.strip()):
            raise ValueError("提醒时间格式必须是 HH:MM")
        return value.strip()

    @field_validator("reminder_timezone")
    @classmethod
    def _normalize_reminder_timezone(cls, value: str | None):
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class PairTaskPlannerSettingsRequest(RequestModel):
    daily_ai_task_count: int | None = Field(default=None, ge=3, le=8)
    reminder_enabled: bool | None = None
    reminder_time: str | None = None
    reminder_timezone: str | None = Field(default=None, max_length=80)

    @field_validator("reminder_time")
    @classmethod
    def _validate_pair_reminder_time(cls, value: str | None):
        if value is None:
            return value
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value.strip()):
            raise ValueError("提醒时间格式必须是 HH:MM")
        return value.strip()

    @field_validator("reminder_timezone")
    @classmethod
    def _normalize_pair_reminder_timezone(cls, value: str | None):
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class PairTaskPlannerSettingsOverridesResponse(BaseModel):
    daily_ai_task_count: int | None = None
    reminder_enabled: bool | None = None
    reminder_time: str | None = None
    reminder_timezone: str | None = None


class PairTaskPlannerSettingsResponse(BaseModel):
    pair_id: uuid.UUID
    overrides: PairTaskPlannerSettingsOverridesResponse = Field(
        default_factory=PairTaskPlannerSettingsOverridesResponse
    )
    effective_settings: TaskPlannerDefaultsResponse


class HabitProfile(RequestModel):
    taboos: list[str] = Field(default_factory=list, max_length=16)
    comfort_preferences: list[str] = Field(default_factory=list, max_length=16)
    custom_notes: str = Field(default='', max_length=200)

    @field_validator('taboos', 'comfort_preferences')
    @classmethod
    def validate_tag_lengths(cls, tags):
        if any(len(tag.strip()) > 32 for tag in tags):
            raise ValueError('每条相处偏好最多32个字')
        return tags


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None = None
    nickname: str
    avatar_url: str | None = None
    wechat_avatar: str | None = None
    testing_unrestricted: bool = False
    wechat_bound: bool = False
    ai_assist_enabled: bool = True
    privacy_mode: Literal["cloud", "local_first"] = "cloud"
    preferred_entry: Literal["daily", "emergency", "reflection"] = "daily"
    preferred_language: Literal["zh", "en", "mixed"] = "zh"
    tone_preference: Literal["gentle", "direct", "warm", "concise"] = "gentle"
    response_length: Literal["short", "medium", "long"] = "medium"
    habit_profile: HabitProfile = Field(default_factory=HabitProfile)
    relationship_space_theme: Literal["classic", "stardust", "engine"] = "classic"
    spiritual_support_enabled: bool = False
    living_region: str = ""
    selected_pair_id: str = ""
    custom_mood_presets: list[str] = Field(default_factory=list)
    hidden_default_moods: list[str] = Field(default_factory=list)
    avatar_presentation: AvatarPresentation = Field(default_factory=AvatarPresentation)
    task_planner_defaults: TaskPlannerDefaultsResponse = Field(
        default_factory=lambda: TaskPlannerDefaultsResponse(
            daily_ai_task_count=5,
            reminder_enabled=True,
            reminder_time="21:00",
            reminder_timezone="Asia/Shanghai",
        )
    )
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("avatar_url", "wechat_avatar", mode="before")
    @classmethod
    def _resolve_user_upload_url(cls, value: str | None):
        return to_client_upload_url(value)


class UserUpdateRequest(RequestModel):
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    avatar_presentation: AvatarPresentation | None = None
    ai_assist_enabled: bool | None = None
    privacy_mode: Literal["cloud", "local_first"] | None = None
    preferred_entry: Literal["daily", "emergency", "reflection"] | None = None
    preferred_language: Literal["zh", "en", "mixed"] | None = None
    tone_preference: Literal["gentle", "direct", "warm", "concise"] | None = None
    response_length: Literal["short", "medium", "long"] | None = None
    habit_profile: HabitProfile | None = None
    relationship_space_theme: Literal["classic", "stardust", "engine"] | None = None
    spiritual_support_enabled: bool | None = None
    living_region: str | None = Field(default=None, max_length=40)
    selected_pair_id: str | None = Field(default=None, max_length=64)
    custom_mood_presets: list[str] | None = None
    hidden_default_moods: list[str] | None = None
    task_planner_defaults: TaskPlannerDefaultsUpdateRequest | None = None


class CrisisSupportChannelResponse(BaseModel):
    id: str
    label: str
    use_when: str


class CrisisSupportResponse(BaseModel):
    urgent_message: str
    channels: list[CrisisSupportChannelResponse] = Field(default_factory=list)
    detected_categories: list[str] = Field(default_factory=list)


class PasswordChangeRequest(RequestModel):
    current_password: str
    new_password: str


# ── 配对 ──


class PairCreateRequest(RequestModel):
    type: Literal["couple", "friend", "spouse", "bestfriend", "parent"] | None = None


class PairUpdateTypeRequest(RequestModel):
    type: Literal["couple", "friend", "spouse", "bestfriend", "parent"]


class PairBreakRequest(RequestModel):
    allow_retention: bool


class PairJoinRequest(RequestModel):
    invite_code: str = Field(
        min_length=INVITE_CODE_LENGTH,
        max_length=INVITE_CODE_LENGTH,
        pattern=INVITE_CODE_PATTERN,
    )

    @field_validator("invite_code", mode="before")
    @classmethod
    def _normalize_invite_code(cls, value: str):
        if isinstance(value, str):
            return normalize_invite_code(value)
        return value


class PairJoinSubmitRequest(PairJoinRequest):
    type: Literal["couple", "friend", "spouse", "bestfriend", "parent"]


class PairChangeDecisionRequest(RequestModel):
    decision: Literal["approve", "reject"]


class PairBreakRetentionRequest(RequestModel):
    message: str = Field(min_length=1, max_length=1000)


class PairBreakMessageRequest(RequestModel):
    message: str = Field(min_length=1, max_length=1000)


class PairBreakRetentionDecisionRequest(RequestModel):
    decision: Literal["accept", "reject"]


class PairChangeRequestMessageResponse(BaseModel):
    id: uuid.UUID
    sender_user_id: uuid.UUID
    sender_nickname: str | None = None
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PairChangeRequestResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    kind: Literal["join_request", "type_change", "break_request"]
    kind_label: str | None = None
    status: Literal["pending", "approved", "rejected", "cancelled"]
    status_label: str | None = None
    requested_type: str | None = None
    requested_type_label: str | None = None
    requester_user_id: uuid.UUID
    requester_nickname: str | None = None
    approver_user_id: uuid.UUID
    approver_nickname: str | None = None
    requested_by_me: bool = False
    waiting_for_me: bool = False
    allow_retention: bool = False
    phase: Literal["awaiting_timeout", "awaiting_retention_choice", "retaining"] | None = None
    expires_at: datetime | None = None
    resolution_reason: Literal[
        "no_retention_timeout",
        "partner_declined",
        "choice_timeout",
        "retention_rejected",
        "retention_timeout",
        "retention_accepted",
        "requester_cancelled",
    ] | None = None
    messages: list[PairChangeRequestMessageResponse] = Field(default_factory=list)
    created_at: datetime
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class PairJoinPreviewResponse(BaseModel):
    pair_id: uuid.UUID
    invite_code: str
    inviter_user_id: uuid.UUID
    inviter_nickname: str | None = None
    current_status: str
    current_status_label: str | None = None
    pending_request: PairChangeRequestResponse | None = None


class PairChangeRequestBundleResponse(BaseModel):
    pair: "PairResponse"
    request: PairChangeRequestResponse


class PairResponse(BaseModel):
    id: uuid.UUID
    user_a_id: uuid.UUID
    user_b_id: uuid.UUID | None
    type: str | None = None
    type_label: str | None = None
    status: str
    status_label: str | None = None
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
    pending_change_request: PairChangeRequestResponse | None = None
    latest_change_request: PairChangeRequestResponse | None = None

    model_config = {"from_attributes": True}

    @field_validator("partner_avatar", mode="before")
    @classmethod
    def _resolve_partner_avatar(cls, value: str | None):
        return to_client_upload_url(value)


class PairSummaryResponse(BaseModel):
    is_paired: bool
    active_pair: PairResponse | None = None
    active_count: int = 0
    pending_count: int = 0


class UpdatePartnerNicknameRequest(RequestModel):
    custom_nickname: str = Field(max_length=50)

    @field_validator("custom_nickname", mode="before")
    @classmethod
    def _normalize_custom_nickname(cls, value: object) -> str:
        return str(value or "").strip()


# ── 打卡 ──


class ClientContextPayload(RequestModel):
    source_type: Literal["text", "image", "voice", "mixed"]
    intent: Literal["daily", "emergency", "crisis", "reflection"]
    risk_level: Literal["none", "watch", "high"] = "none"
    risk_hits: list[str] = Field(default_factory=list)
    pii_summary: dict | None = None
    privacy_mode: Literal["cloud", "local_first"] = "cloud"
    upload_policy: Literal["full", "redacted_only", "local_only"] = "full"
    redacted_text: str | None = None
    client_tags: list[str] = Field(default_factory=list)
    device_meta: dict | None = None
    ai_assist_enabled: bool | None = None
    archive_insight: dict | None = None


class CheckinRequest(RequestModel):
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
    client_context: ClientContextPayload | None = None


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
    client_context: ClientContextPayload | None = None
    analysis_source: Literal[
        "rule", "client_precheck", "server_ai", "rule+server_ai"
    ] | None = None
    client_precheck: ClientContextPayload | None = None
    server_analysis: dict | None = None
    final_guidance: str | None = None
    safety_gate: bool = False
    checkin_date: date
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("image_url", "voice_url", mode="before")
    @classmethod
    def _resolve_checkin_upload_url(cls, value: str | None):
        return to_client_upload_url(value)


# ── 报告 ──


class ReportResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    type: str
    status: str
    content: dict | None = None
    health_score: float | None = None
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str | None = None
    safety_handoff: str | None = None
    report_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportScopeOptionResponse(BaseModel):
    pair_id: uuid.UUID
    partner_label: str
    pair_type: str | None = None
    pair_type_label: str
    sort_score: int
    activity_score: int
    dual_activity_score: int
    health_score: int
    latest_report_date: date | None = None
    latest_signal_at: datetime | None = None
    reason_tags: list[str] = Field(default_factory=list)


class WeeklyAssessmentAnswerItem(RequestModel):
    item_id: str | None = None
    dim: str
    score: int = Field(ge=0, le=100)
    option_id: str | None = None


class WeeklyAssessmentDimensionScoreResponse(BaseModel):
    id: str
    label: str
    score: int | None = None
    status: str


class WeeklyAssessmentPointResponse(BaseModel):
    event_id: uuid.UUID
    submitted_at: str
    total_score: int
    dimension_scores: list[WeeklyAssessmentDimensionScoreResponse] = Field(
        default_factory=list
    )
    scope: str
    change_summary: str | None = None


class WeeklyAssessmentSubmitRequest(RequestModel):
    answers: list[WeeklyAssessmentAnswerItem] = Field(default_factory=list)
    submitted_at: datetime | None = None


class WeeklyAssessmentLatestResponse(BaseModel):
    event_id: uuid.UUID
    submitted_at: str
    total_score: int
    dimension_scores: list[WeeklyAssessmentDimensionScoreResponse] = Field(
        default_factory=list
    )
    scope: str
    change_summary: str | None = None


class WeeklyAssessmentTrendResponse(BaseModel):
    latest_score: int | None = None
    dimension_scores: list[WeeklyAssessmentDimensionScoreResponse] = Field(
        default_factory=list
    )
    trend_points: list[WeeklyAssessmentPointResponse] = Field(default_factory=list)
    change_summary: str


class WeeklyAssessmentOptionResponse(BaseModel):
    id: str
    label: str
    score: int


class WeeklyAssessmentItemResponse(BaseModel):
    item_id: str
    track: str
    dimension: str
    dimension_label: str
    prompt: str
    options: list[WeeklyAssessmentOptionResponse] = Field(default_factory=list)
    rotation_group: str
    active: bool = True
    version: str = "v1"


class WeeklyAssessmentPackResponse(BaseModel):
    title: str
    subtitle: str | None = None
    latest_score: int | None = None
    change_summary: str | None = None
    items: list[WeeklyAssessmentItemResponse] = Field(default_factory=list)
    generated_at: str


class SafetyStatusResponse(BaseModel):
    risk_level: str
    risk_level_label: str | None = None
    why_now: str
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str
    recommended_action: str
    handoff_recommendation: str | None = None
    crisis_support: CrisisSupportResponse | None = None


class PrivacyDeleteRequestResponse(BaseModel):
    id: uuid.UUID
    status: str
    requested_at: datetime
    scheduled_for: datetime
    cancelled_at: datetime | None = None
    executed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None
    review_note: str | None = None
    can_cancel: bool = False


class PrivacyBenchmarkSummaryResponse(BaseModel):
    cases_total: int
    raw_sensitive_hits: int
    proxied_sensitive_hits: int
    leak_reduction_pct: float
    avg_utility_pct: float
    replacement_total: int
    runtime_profile: str
    text_pipeline: str
    audio_pipeline: str


class PrivacyBenchmarkCaseResponse(BaseModel):
    case_id: str
    title: str
    original_text: str
    proxied_text: str
    raw_sensitive_hits: int
    proxied_sensitive_hits: int
    utility_pct: float
    replacement_count: int
    entity_counts: dict[str, int] = Field(default_factory=dict)


class PrivacyBenchmarkRunResponse(BaseModel):
    run_id: uuid.UUID | None = None
    occurred_at: datetime
    summary: PrivacyBenchmarkSummaryResponse
    cases: list[PrivacyBenchmarkCaseResponse] = Field(default_factory=list)


class PrivacyStatusResponse(BaseModel):
    sandbox_enabled: bool
    log_masking: bool
    llm_redaction: bool
    privacy_mode: Literal["cloud", "local_first"] = "cloud"
    private_upload_access: bool
    audit_enabled: bool
    text_proxy_enabled: bool = False
    text_proxy_strategy: str = "redact_only"
    audio_pipeline_mode: str = "cloud_transcription"
    runtime_profile: str = "2c2g_text_proxy"
    audit_retention_days: int
    upload_ticket_ttl_minutes: int
    delete_grace_days: int
    latest_delete_request: PrivacyDeleteRequestResponse | None = None
    last_benchmark_summary: PrivacyBenchmarkSummaryResponse | None = None


class PrivacyAuditEntryResponse(BaseModel):
    event_id: uuid.UUID
    event_type: str
    event_label: str
    summary: str = ""
    occurred_at: datetime
    meta: dict | None = None


class PrivacyDeleteReviewRequest(RequestModel):
    note: str | None = Field(default=None, max_length=200)


class AdminPrivacyAuditEntryResponse(PrivacyAuditEntryResponse):
    user_id: uuid.UUID | None = None
    pair_id: uuid.UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    source: str | None = None


class AdminPrivacyDeleteRequestResponse(PrivacyDeleteRequestResponse):
    user_id: uuid.UUID
    user_email: str | None = None
    user_nickname: str | None = None


class PrivacyRetentionSweepResponse(BaseModel):
    dry_run: bool
    expired_privacy_events: int
    stale_temp_files: int
    expired_raw_checkins: int = 0
    deleted_raw_uploads: int = 0
    due_requests: int | None = None
    executed: int | None = None
    manual_review: int | None = None


# ── 关系任务 ──


class TaskResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID
    user_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    title: str
    description: str
    category: str
    source: str = "system"
    importance_level: Literal["low", "medium", "high"] = "medium"
    status: str
    due_date: date
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskCreateRequest(RequestModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=400)
    category: str = Field(default="activity", min_length=1, max_length=30)
    target_scope: Literal["self", "both"] = "self"
    due_date: date | None = None
    parent_task_id: uuid.UUID | None = None
    importance_level: Literal["low", "medium", "high"] = "medium"


class TaskUpdateRequest(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=400)
    category: str | None = Field(default=None, min_length=1, max_length=30)
    target_scope: Literal["self", "both"] | None = None
    due_date: date | None = None
    importance_level: Literal["low", "medium", "high"] | None = None


class TaskFeedbackRequest(RequestModel):
    outcome: Literal["helped", "not_yet", "difficult", "uncertain"] | None = None
    usefulness_score: int | None = Field(default=None, ge=1, le=5)
    friction_score: int | None = Field(default=None, ge=1, le=5)
    relationship_shift_score: int | None = Field(default=None, ge=-2, le=2)
    note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _require_feedback(self):
        if self.outcome is None and not str(self.note or '').strip() and all(value is None for value in (
            self.usefulness_score, self.friction_score, self.relationship_shift_score,
        )):
            raise ValueError("选一下实际感受，或补充一句")
        return self


class TaskFeedbackResponse(BaseModel):
    task_id: uuid.UUID
    outcome: Literal["helped", "not_yet", "difficult", "uncertain"] | None = None
    usefulness_score: int | None = None
    friction_score: int | None = None
    relationship_shift_score: int | None = None
    note: str | None = None
    submitted_at: datetime


class TaskResultRequest(RequestModel):
    status: Literal["pending", "completed"]
    feedback: TaskFeedbackRequest | None

    @model_validator(mode="after")
    def _consistent_result(self):
        if self.feedback is not None:
            if self.status == 'completed' and self.feedback.outcome == 'not_yet':
                raise ValueError('已完成的安排不能选择还没做')
            if self.status == 'pending' and self.feedback.outcome not in {'not_yet', 'difficult'}:
                raise ValueError('未完成的安排先记录实际进展')
        return self


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


class CrisisAcknowledgeRequest(RequestModel):
    """用户确认已查看预警"""

    pass


class CrisisResolveRequest(RequestModel):
    """用户标记预警已解决"""

    note: str | None = None


class CrisisEscalateRequest(RequestModel):
    """升级至专业帮助"""

    reason: str | None = None


# ── 关系智能（Insights） ──


class RelationshipProfileSnapshotResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    window_days: int
    snapshot_date: date
    metrics_json: dict
    risk_summary: dict | None = None
    attachment_summary: dict | None = None
    suggested_focus: dict | None = None
    behavior_summary: dict | None = None
    generated_from_event_at: datetime | None = None
    version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InterventionPlanResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    trigger_event_id: uuid.UUID | None = None
    trigger_snapshot_id: uuid.UUID | None = None
    risk_level: str
    goal_json: dict | None = None
    status: str
    start_date: date
    end_date: date | None = None
    owner_version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RelationshipTimelineEventResponse(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    event_type: str
    label: str
    summary: str
    detail: str | None = None
    category: str
    category_label: str
    tone: str
    tone_label: str
    entity_type: str | None = None
    entity_id: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    payload: dict | None = None


class RelationshipTimelineResponse(BaseModel):
    scope: str
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    event_count: int = 0
    latest_event_at: datetime | None = None
    highlights: list[str] = Field(default_factory=list)
    events: list[RelationshipTimelineEventResponse] = Field(default_factory=list)


class RelationshipTimelineArchiveRecordResponse(BaseModel):
    content: str | None = None
    mood_tags: list[str] = Field(default_factory=list)
    sentiment_score: float | None = None
    mood_score: int | None = None
    interaction_freq: int | None = None
    interaction_initiative: str | None = None
    deep_conversation: bool | None = None
    task_completed: bool | None = None
    image: dict | None = None
    voice: dict | None = None
    archive_insight: dict | None = None
    client_context_preview: dict | None = None


class RelationshipTimelineArchiveReportResponse(BaseModel):
    report_type: str
    status: str
    health_score: float | None = None
    report_date: date
    summary: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    content: dict | None = None


class RelationshipTimelineArchiveItemResponse(BaseModel):
    id: uuid.UUID
    item_type: str
    occurred_at: datetime
    local_date: date
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    visibility: str
    locked_reason: str | None = None
    has_raw_content: bool = False
    has_image_original: bool = False
    has_voice_original: bool = False
    raw_retention_until: datetime | None = None
    raw_deleted_at: datetime | None = None
    download_available: bool = False
    record: RelationshipTimelineArchiveRecordResponse | None = None
    report: RelationshipTimelineArchiveReportResponse | None = None


class RelationshipTimelineArchiveResponse(BaseModel):
    scope: str
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    item_count: int = 0
    latest_item_at: datetime | None = None
    next_before: str | None = None
    items: list[RelationshipTimelineArchiveItemResponse] = Field(default_factory=list)


class RelationshipTimelineMetricResponse(BaseModel):
    label: str
    value: str


class RelationshipTimelineEvidenceCardResponse(BaseModel):
    title: str
    body: str
    tone: str | None = None


class RelationshipTimelineCurrentContextResponse(BaseModel):
    active_plan_type: str | None = None
    active_branch_label: str | None = None
    momentum: str | None = None
    risk_level: str | None = None
    latest_report_insight: str | None = None
    recommended_next_action: str | None = None


class RelationshipTimelineEventDetailResponse(BaseModel):
    event: RelationshipTimelineEventResponse
    event_summary: str | None = None
    metrics: list[RelationshipTimelineMetricResponse] = Field(default_factory=list)
    evidence_cards: list[RelationshipTimelineEvidenceCardResponse] = Field(
        default_factory=list
    )
    impact_modules: list[str] = Field(default_factory=list)
    recommended_next_action: str | None = None
    current_context: RelationshipTimelineCurrentContextResponse | None = None


class MessageSimulationRequest(RequestModel):
    draft: str


class DecisionFeedbackRequest(RequestModel):
    feedback_type: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, max_length=200)


class MessageSimulationResponse(BaseModel):
    event_id: uuid.UUID | None = None
    draft: str
    partner_view: str
    likely_impact: str
    risk_level: str
    risk_level_label: str | None = None
    risk_reason: str
    safer_rewrite: str
    suggested_tone: str
    conversation_goal: str | None = None
    do_list: list[str] = Field(default_factory=list)
    avoid_list: list[str] = Field(default_factory=list)
    algorithm_version: str | None = None
    confidence: float | None = None
    decision_trace: dict[str, Any] = Field(default_factory=dict)
    focus_labels: list[str] = Field(default_factory=list)
    risk_score: float | None = None
    baseline_delta: float | None = None
    fallback_reason: str | None = None
    shadow_result: dict[str, Any] | None = None
    feedback_status: str | None = None
    baseline_match: str | None = None
    deviation_score: float | None = None
    deviation_reasons: list[str] = Field(default_factory=list)
    reaction_shift: str | None = None
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str | None = None
    safety_handoff: str | None = None
    crisis_support: CrisisSupportResponse | None = None


class RepairProtocolStepResponse(BaseModel):
    sequence: int
    title: str
    action: str
    why: str | None = None
    duration_hint: str | None = None


class TheoryBasisResponse(BaseModel):
    id: str
    name: str
    evidence_level: str
    evidence_label: str
    summary: str
    how_it_is_used: str
    boundary: str


class RepairProtocolResponse(BaseModel):
    protocol_type: str
    protocol_type_label: str | None = None
    level: str
    level_label: str | None = None
    title: str
    summary: str
    timing_hint: str | None = None
    active_plan_type: str | None = None
    active_plan_type_label: str | None = None
    model_family: str | None = None
    model_family_label: str | None = None
    clinical_disclaimer: str | None = None
    focus_tags: list[str] = Field(default_factory=list)
    focus_tag_labels: list[str] = Field(default_factory=list)
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)
    steps: list[RepairProtocolStepResponse] = Field(default_factory=list)
    do_not: list[str] = Field(default_factory=list)
    success_signal: str | None = None
    escalation_rule: str | None = None
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str | None = None
    safety_handoff: str | None = None


# ── 智能陪伴 (Agent) ──


class InterventionScorecardResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    status: str
    risk_level: str
    primary_goal: str | None = None
    focus: list[str] = Field(default_factory=list)
    start_date: date
    end_date: date | None = None
    duration_days: int
    risk_before: str | None = None
    risk_now: str | None = None
    health_before: float | None = None
    health_now: float | None = None
    health_delta: float | None = None
    completion_rate: float = 0.0
    completed_task_count: int = 0
    total_task_count: int = 0
    feedback_count: int = 0
    usefulness_avg: float | None = None
    friction_avg: float | None = None
    momentum: str
    wins: list[str] = Field(default_factory=list)
    watchouts: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class EvaluationMetricResponse(BaseModel):
    id: str
    label: str
    status: str
    summary: str
    baseline: str | None = None
    current: str | None = None
    delta: str | None = None
    note: str | None = None


class InterventionEvaluationResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    evaluation_model: str
    evaluation_label: str
    verdict: str
    verdict_label: str
    confidence_level: str
    confidence_label: str
    data_quality_level: str
    data_quality_label: str
    summary: str
    primary_metrics: list[EvaluationMetricResponse] = Field(default_factory=list)
    process_metrics: list[EvaluationMetricResponse] = Field(default_factory=list)
    recommendation: str
    recommendation_label: str
    recommendation_reason: str
    data_gaps: list[str] = Field(default_factory=list)
    next_measurements: list[str] = Field(default_factory=list)
    scientific_note: str
    clinical_disclaimer: str
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)


class ExperimentPolicyResponse(BaseModel):
    signature: str
    label: str
    branch: str
    branch_label: str
    intensity: str
    intensity_label: str
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    category_copy_modes: dict[str, str] = Field(default_factory=dict)


class ExperimentObservationResponse(BaseModel):
    snapshot_key: str
    observed_on: str
    summary: str | None = None
    verdict: str
    verdict_label: str
    confidence_level: str
    confidence_label: str
    data_quality_level: str
    data_quality_label: str
    completion_rate: float | None = None
    risk_now: str | None = None
    usefulness_avg: float | None = None
    friction_avg: float | None = None
    recommendation: str | None = None
    recommendation_label: str | None = None
    is_current: bool = False
    policy: ExperimentPolicyResponse


class ExperimentVariantResponse(BaseModel):
    signature: str
    label: str | None = None
    branch: str | None = None
    branch_label: str | None = None
    intensity: str | None = None
    intensity_label: str | None = None
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    observation_count: int = 0
    positive_count: int = 0
    mixed_count: int = 0
    negative_count: int = 0
    insufficient_count: int = 0
    avg_completion_rate: float | None = None
    avg_usefulness: float | None = None
    avg_friction: float | None = None
    last_observed_on: str | None = None
    latest_verdict: str | None = None
    latest_verdict_label: str | None = None
    is_current: bool = False
    summary: str | None = None


class InterventionExperimentLedgerResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    experiment_model: str
    experiment_label: str
    hypothesis: str
    current_policy: ExperimentPolicyResponse
    comparison_status: str
    comparison_label: str
    comparison_summary: str
    recommendation: str | None = None
    recommendation_label: str | None = None
    recommendation_reason: str | None = None
    evidence_points: list[ExperimentObservationResponse] = Field(default_factory=list)
    strategy_variants: list[ExperimentVariantResponse] = Field(default_factory=list)
    next_question: str
    scientific_note: str
    clinical_disclaimer: str
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)


class RegisteredPolicyResponse(BaseModel):
    policy_id: str
    plan_type: str | None = None
    title: str
    summary: str
    branch: str | None = None
    branch_label: str | None = None
    intensity: str | None = None
    intensity_label: str | None = None
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    when_to_use: str
    success_marker: str
    guardrail: str
    version: str | None = None
    status: str | None = None
    source: str | None = None
    observation_count: int = 0
    latest_verdict: str | None = None
    latest_verdict_label: str | None = None
    avg_completion_rate: float | None = None
    avg_usefulness: float | None = None
    avg_friction: float | None = None
    summary_note: str | None = None
    signature: str | None = None
    is_current: bool = False
    is_recommended: bool = False
    selection_reason: str | None = None


class PolicyLibraryItemResponse(BaseModel):
    id: uuid.UUID
    policy_id: str
    plan_type: str
    title: str
    summary: str
    branch: str
    branch_label: str
    intensity: str
    intensity_label: str
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    when_to_use: str
    success_marker: str
    guardrail: str
    version: str
    status: str
    source: str
    sort_order: int
    metadata_json: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyLibraryCreateRequest(RequestModel):
    policy_id: str
    plan_type: str
    title: str
    summary: str
    branch: str
    branch_label: str
    intensity: str
    intensity_label: str
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    when_to_use: str
    success_marker: str
    guardrail: str
    version: str = "v1"
    status: Literal["active", "inactive"] = "active"
    metadata_json: dict | None = None


class PolicyLibraryUpdateRequest(RequestModel):
    plan_type: str | None = None
    title: str | None = None
    summary: str | None = None
    branch: str | None = None
    branch_label: str | None = None
    intensity: str | None = None
    intensity_label: str | None = None
    copy_mode: str | None = None
    copy_mode_label: str | None = None
    when_to_use: str | None = None
    success_marker: str | None = None
    guardrail: str | None = None
    version: str | None = None
    status: Literal["active", "inactive"] | None = None
    metadata_json: dict | None = None


class PolicyLibraryToggleRequest(RequestModel):
    status: Literal["active", "inactive"] | None = None


class PolicyLibraryReorderRequest(RequestModel):
    policy_ids: list[str] = Field(default_factory=list)


class PolicyLibraryRollbackRequest(RequestModel):
    target_event_id: uuid.UUID
    note: str | None = None


class PolicyAuditActorResponse(BaseModel):
    user_id: uuid.UUID | None = None
    email: str | None = None


class PolicyAuditChangeResponse(BaseModel):
    field: str
    label: str
    before_value: Any | None = None
    after_value: Any | None = None


class PolicyAuditEntryResponse(BaseModel):
    event_id: uuid.UUID
    event_type: str
    event_label: str
    summary: str | None = None
    occurred_at: datetime
    note: str | None = None
    actor: PolicyAuditActorResponse | None = None
    before: dict | None = None
    after: dict | None = None
    changed_fields: list[PolicyAuditChangeResponse] = Field(default_factory=list)
    meta: dict | None = None
    can_restore: bool = False


class PolicyRegistrySnapshotResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    registry_label: str
    selection_mode: str | None = None
    selection_label: str | None = None
    selection_reason: str | None = None
    current_policy: RegisteredPolicyResponse
    recommended_policy: RegisteredPolicyResponse | None = None
    policies: list[RegisteredPolicyResponse] = Field(default_factory=list)
    scientific_note: str
    clinical_disclaimer: str


class PolicyScheduleMetricResponse(BaseModel):
    id: str
    label: str
    current: str | None = None
    target: str
    why: str | None = None


class PolicyScheduleStageResponse(BaseModel):
    phase: str
    phase_label: str
    title: str
    summary: str
    policy_id: str | None = None
    days_total: int
    days_observed: int = 0
    days_remaining: int = 0
    min_observations: int = 0
    observations_remaining: int = 0
    checkpoint_date: date | None = None
    branch_label: str | None = None
    intensity_label: str | None = None
    copy_mode_label: str | None = None


class PolicyScheduleResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    scheduler_model: str
    scheduler_label: str
    schedule_mode: str
    schedule_label: str
    current_policy: RegisteredPolicyResponse
    recommended_policy: RegisteredPolicyResponse | None = None
    current_stage: PolicyScheduleStageResponse
    next_stage: PolicyScheduleStageResponse | None = None
    fallback_stage: PolicyScheduleStageResponse | None = None
    measurement_plan: list[PolicyScheduleMetricResponse] = Field(default_factory=list)
    advance_when: list[str] = Field(default_factory=list)
    hold_when: list[str] = Field(default_factory=list)
    backoff_when: list[str] = Field(default_factory=list)
    scientific_note: str
    clinical_disclaimer: str


class PolicyDecisionAuditTrailResponse(BaseModel):
    occurred_at: datetime
    summary: str
    selection_mode: str | None = None
    selection_label: str | None = None
    schedule_mode: str | None = None
    schedule_label: str | None = None
    selected_policy_signature: str | None = None
    selected_policy_label: str | None = None
    auto_applied: bool = False
    checkpoint_date: date | None = None


class PolicyDecisionAuditResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    plan_type: str
    audit_label: str
    decision_model: str
    current_policy: RegisteredPolicyResponse
    recommended_policy: RegisteredPolicyResponse | None = None
    selection_mode: str | None = None
    selection_label: str | None = None
    selection_reason: str | None = None
    schedule_mode: str | None = None
    schedule_label: str | None = None
    schedule_summary: str | None = None
    active_branch_label: str | None = None
    next_checkpoint: date | None = None
    evidence_observation_count: int = 0
    signals: list[RelationshipTimelineMetricResponse] = Field(default_factory=list)
    supporting_events: list[RelationshipTimelineEventResponse] = Field(
        default_factory=list
    )
    decision_history: list[PolicyDecisionAuditTrailResponse] = Field(
        default_factory=list
    )
    scientific_note: str
    clinical_disclaimer: str


class RelationshipPlaybookDayResponse(BaseModel):
    day_index: int
    label: str
    title: str
    theme: str
    objective: str
    action: str
    success_signal: str | None = None
    checkin_prompt: str | None = None
    branch_mode: str
    branch_mode_label: str
    status: str


class PlaybookTransitionResponse(BaseModel):
    id: uuid.UUID
    transition_type: str
    trigger_type: str
    trigger_summary: str | None = None
    from_day: int | None = None
    to_day: int
    from_branch: str | None = None
    from_branch_label: str | None = None
    to_branch: str
    to_branch_label: str
    created_at: datetime
    is_new: bool = False


class RelationshipPlaybookResponse(BaseModel):
    plan_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    run_status: str | None = None
    plan_type: str
    title: str
    summary: str
    primary_goal: str | None = None
    momentum: str
    risk_level: str
    active_branch: str
    active_branch_label: str
    branch_reason: str
    focus_tags: list[str] = Field(default_factory=list)
    model_family: str | None = None
    clinical_disclaimer: str | None = None
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)
    current_day: int
    total_days: int
    branch_started_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_viewed_at: datetime | None = None
    transition_count: int = 0
    latest_transition: PlaybookTransitionResponse | None = None
    today_card: RelationshipPlaybookDayResponse
    days: list[RelationshipPlaybookDayResponse] = Field(default_factory=list)


class PlaybookHistoryResponse(BaseModel):
    run_id: uuid.UUID
    plan_id: uuid.UUID
    plan_type: str
    run_status: str
    active_branch: str
    active_branch_label: str
    current_day: int
    transition_count: int = 0
    transitions: list[PlaybookTransitionResponse] = Field(default_factory=list)


class MethodologyResponse(BaseModel):
    system_name: str
    system_name_label: str | None = None
    model_family: str
    model_family_label: str | None = None
    measurement_model: list[str] = Field(default_factory=list)
    decision_model: list[str] = Field(default_factory=list)
    active_modules: list[str] = Field(default_factory=list)
    current_focus: list[str] = Field(default_factory=list)
    disclaimer: str
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)


class NarrativeAlignmentResponse(BaseModel):
    event_id: uuid.UUID | None = None
    pair_id: uuid.UUID
    checkin_date: date
    user_a_label: str
    user_b_label: str
    alignment_score: int
    shared_story: str
    view_a_summary: str
    view_b_summary: str
    misread_risk: str
    divergence_points: list[str] = Field(default_factory=list)
    bridge_actions: list[str] = Field(default_factory=list)
    suggested_opening: str | None = None
    coach_note: str | None = None
    algorithm_version: str | None = None
    confidence: float | None = None
    decision_trace: dict[str, Any] = Field(default_factory=dict)
    focus_labels: list[str] = Field(default_factory=list)
    risk_score: float | None = None
    baseline_delta: float | None = None
    fallback_reason: str | None = None
    shadow_result: dict[str, Any] | None = None
    feedback_status: str | None = None
    reaction_shift: str | None = None
    deviation_reasons: list[str] = Field(default_factory=list)
    history_sufficiency: str | None = None
    current_risk_level: str | None = None
    active_plan_type: str | None = None
    source: Literal["ai", "fallback"] = "ai"
    is_fallback: bool = False
    generated_at: datetime


class UserInteractionEventRequest(RequestModel):
    pair_id: uuid.UUID | None = None
    session_id: str | None = Field(default=None, max_length=80)
    source: Literal["client", "server", "agent", "insights", "system"] = "client"
    event_type: str = Field(min_length=1, max_length=80)
    page: str | None = Field(default=None, max_length=80)
    path: str | None = Field(default=None, max_length=255)
    target_type: str | None = Field(default=None, max_length=50)
    target_id: str | None = Field(default=None, max_length=80)
    payload: dict | None = None


class UserInteractionEventResponse(BaseModel):
    event_id: uuid.UUID
    accepted: bool = True


class AgentSessionResponse(BaseModel):
    session_id: uuid.UUID
    has_extracted_checkin: bool
    expires_at: datetime | None = None
    reused: bool = False


class AgentSessionListItemResponse(BaseModel):
    session_id: uuid.UUID
    pair_id: uuid.UUID | None = None
    status: str
    topic: str
    last_message: str = ""
    message_count: int = 0
    has_extracted_checkin: bool = False
    session_date: date
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None


class AgentMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    payload: dict | None = None


class AgentLabeledCodePayload(BaseModel):
    code: str | None = None
    label: str | None = None


class VoiceEvidencePayload(RequestModel):
    voice_url: str | None = None
    transcript_text: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    source: Literal["realtime", "upload"]
    voice_emotion: AgentLabeledCodePayload | None = None
    content_emotion: dict[str, Any] | None = None
    transcript_language: AgentLabeledCodePayload | None = None


class AgentSceneContext(RequestModel):
    source_label: str = Field(default="当前记录", max_length=100)
    summary: str = Field(default="", max_length=3200)
    intent: Literal["auto", "listen", "wording", "plan", "reflect"] = "auto"


class AgentChatRequest(RequestModel):
    content: str = ""
    client_message_id: uuid.UUID | None = None
    surface: Literal["chat", "checkin_assist"] = "checkin_assist"
    voice_evidence: VoiceEvidencePayload | None = None
    multi_agent: bool = False
    scene_context: AgentSceneContext | None = None

    @model_validator(mode="after")
    def _validate_message_content(self):
        content = str(self.content or "").strip()
        transcript = str(
            getattr(self.voice_evidence, "transcript_text", "") or ""
        ).strip()
        if content or transcript:
            return self
        raise ValueError("文字内容和语音转写至少填写一项")


class AgentThoughtTraceResponse(BaseModel):
    step_index: int
    thought: str | None = None
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    duration_ms: float | None = None


class AgentChatResponse(BaseModel):
    reply: str
    action: str
    message_id: uuid.UUID | None = None
    task_proposals: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[AgentThoughtTraceResponse] = []


class AgentCheckupResponse(BaseModel):
    """主动巡查 Agent 的产出：诊断报告 + 干预建议 + 采纳可执行的巡查动作。"""

    report: str
    health: int | None = Field(default=None, ge=0, le=100)
    risk_level: str = "unknown"
    risk_reason: str = ""
    recommended_actions: list[str] = []
    urgency: str = "monitor"
    trace: list[AgentThoughtTraceResponse] = []
    generated_at: datetime | None = None


class AgentRealtimeTicketResponse(BaseModel):
    ticket: str
    expires_in: int


class SwarmRoleStepResponse(BaseModel):
    role: str
    role_name: str
    summary: str
    status: str = "ok"
    duration_ms: float | None = None


class AgentSwarmResponse(BaseModel):
    """多智能体协作产出：最终回复 + 每个角色的协作轨迹。"""

    reply: str
    action: str = "chat"
    message_id: uuid.UUID | None = None
    task_proposals: list[dict[str, Any]] = Field(default_factory=list)
    swarm: list[SwarmRoleStepResponse] = []
    trace: list[AgentThoughtTraceResponse] = []


PairChangeRequestBundleResponse.model_rebuild()

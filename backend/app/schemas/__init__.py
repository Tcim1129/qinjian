"""Pydantic 请求/响应模型"""

import uuid
from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


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


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


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


class PairSummaryResponse(BaseModel):
    is_paired: bool
    active_pair: PairResponse | None = None
    active_count: int = 0
    pending_count: int = 0


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
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str | None = None
    safety_handoff: str | None = None
    report_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyAssessmentAnswerItem(BaseModel):
    dim: str
    score: int = Field(ge=0, le=100)


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


class WeeklyAssessmentSubmitRequest(BaseModel):
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


class SafetyStatusResponse(BaseModel):
    risk_level: str
    why_now: str
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str
    recommended_action: str
    handoff_recommendation: str | None = None


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


class TaskFeedbackRequest(BaseModel):
    usefulness_score: int = Field(ge=1, le=5)
    friction_score: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=200)


class TaskFeedbackResponse(BaseModel):
    task_id: uuid.UUID
    usefulness_score: int
    friction_score: int
    note: str | None = None
    submitted_at: datetime


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
    metrics: list[RelationshipTimelineMetricResponse] = Field(default_factory=list)
    evidence_cards: list[RelationshipTimelineEvidenceCardResponse] = Field(
        default_factory=list
    )
    current_context: RelationshipTimelineCurrentContextResponse | None = None


class MessageSimulationRequest(BaseModel):
    draft: str


class MessageSimulationResponse(BaseModel):
    draft: str
    partner_view: str
    likely_impact: str
    risk_level: str
    risk_reason: str
    safer_rewrite: str
    suggested_tone: str
    conversation_goal: str | None = None
    do_list: list[str] = Field(default_factory=list)
    avoid_list: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    limitation_note: str | None = None
    safety_handoff: str | None = None


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
    level: str
    title: str
    summary: str
    timing_hint: str | None = None
    active_plan_type: str | None = None
    model_family: str | None = None
    clinical_disclaimer: str | None = None
    focus_tags: list[str] = Field(default_factory=list)
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


class PolicyLibraryCreateRequest(BaseModel):
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


class PolicyLibraryUpdateRequest(BaseModel):
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


class PolicyLibraryToggleRequest(BaseModel):
    status: Literal["active", "inactive"] | None = None


class PolicyLibraryReorderRequest(BaseModel):
    policy_ids: list[str] = Field(default_factory=list)


class PolicyLibraryRollbackRequest(BaseModel):
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
    model_family: str
    measurement_model: list[str] = Field(default_factory=list)
    decision_model: list[str] = Field(default_factory=list)
    active_modules: list[str] = Field(default_factory=list)
    current_focus: list[str] = Field(default_factory=list)
    disclaimer: str
    theory_basis: list[TheoryBasisResponse] = Field(default_factory=list)


class NarrativeAlignmentResponse(BaseModel):
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
    current_risk_level: str | None = None
    active_plan_type: str | None = None
    generated_at: datetime


class AgentSessionResponse(BaseModel):
    session_id: uuid.UUID
    has_extracted_checkin: bool


class AgentMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    payload: dict | None = None


class AgentChatRequest(BaseModel):
    content: str


class AgentChatResponse(BaseModel):
    reply: str
    action: str

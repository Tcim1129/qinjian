"""移动端（App / 小程序）接口：预检、启动聚合、今日、打卡与可见性。

设计依据：docs/plans/打卡可见性设计.md
只复用现有服务与模型，不改动网页端既有行为。
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.api.v1.agent import simulate_message, submit_message_decision_feedback
from app.api.v1.upload import _save_file
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    MEDIA_UPLOAD_TICKET_TTL_SECONDS,
    create_media_upload_ticket,
    create_realtime_ws_ticket,
    decode_media_upload_ticket,
)
from app.core.time import current_local_date
from app.models import (
    Checkin,
    MobileMediaUpload,
    MobileOfflineDraft,
    MobilePushRegistration,
    Pair,
    PairStatus,
    RelationshipEvent,
    RelationshipTask,
    Report,
    ReportStatus,
    ReportType,
    TaskImportance,
    TaskStatus,
    UploadAsset,
    User,
    UserNotification,
)
from app.schemas import (
    DecisionFeedbackRequest,
    MessageSimulationRequest,
    MessageSimulationStructuredResult,
    MobileActionCompleteRequest,
    MobileActionFeedbackRequest,
    MobileActionFeedbackResponse,
    MobileActionItemResponse,
    MobileActionListRequest,
    MobileBootstrapAccountResponse,
    MobileBootstrapNotificationsResponse,
    MobileBootstrapRelationshipResponse,
    MobileBootstrapRealtimeVoiceResponse,
    MobileBootstrapRequest,
    MobileBootstrapResponse,
    MobileCheckinCorrectionRequest,
    MobileCheckinCorrectionResponse,
    MobileCheckinCreateRequest,
    MobileCheckinCreateResponse,
    MobileCheckinDeleteRequest,
    MobileCheckinDeleteResponse,
    MobileCheckinDetailRequest,
    MobileCheckinDetailResponse,
    MobileCheckinMediaChangeRequest,
    MobileCheckinMediaChangeResponse,
    MobileCheckinVisibilityChangeRequest,
    MobileCheckinVisibilityChangeResponse,
    MobileCheckinVisibilityRequest,
    MobileCheckinVisibilityResponse,
    MobileClientLoginMethodResponse,
    MobileClientPreflightRequest,
    MobileClientPreflightResponse,
    MobileMediaAccessRequest,
    MobileMediaAccessResponse,
    MobileMediaCancelRequest,
    MobileMediaCancelResponse,
    MobileMediaDiscardRequest,
    MobileMediaDiscardResponse,
    MobileMediaPreflightRequest,
    MobileMediaPreflightResponse,
    MobileMediaStatusRequest,
    MobileMediaStatusResponse,
    MobileMediaUploadResponse,
    MobileMessageSimulationFeedbackRequest,
    MobileMessageSimulationFeedbackResponse,
    MobileMessageSimulationRequest,
    MobileMessageSimulationResponse,
    MobileNotificationItemResponse,
    MobileNotificationListRequest,
    MobileNotificationListResponse,
    MobileNotificationPreferenceChangeRequest,
    MobileNotificationPreferenceMutationResponse,
    MobileNotificationPreferenceResponse,
    MobileNotificationPreferenceSubscriptionRequest,
    MobileNotificationPreferencesStatusResponse,
    MobileNotificationQuietHours,
    MobileNotificationReadAllRequest,
    MobileNotificationReadRequest,
    MobileNotificationReadResponse,
    MobileNarrativeAlignmentFeedbackRequest,
    MobileNarrativeAlignmentFeedbackResponse,
    MobileNarrativeAlignmentRequest,
    MobileNarrativeAlignmentResponse,
    MobileOfflineDraftAdoptRequest,
    MobileOfflineDraftDetailResponse,
    MobileOfflineDraftDiscardRequest,
    MobileOfflineDraftListRequest,
    MobileOfflineDraftListResponse,
    MobileOfflineDraftMetadataResponse,
    MobileOfflineDraftPayload,
    MobileOfflineDraftPullRequest,
    MobileOfflineDraftRecoverRequest,
    MobileOfflineDraftSyncRequest,
    PushPermissionSyncRequest,
    PushReceiptRequest,
    PushReceiptResponse,
    PushRegistrationRequest,
    PushRegistrationResponse,
    PushRegistrationStatusRequest,
    PushRegistrationStatusResponse,
    MobileRealtimeVoiceTicketRequest,
    MobileRealtimeVoiceTicketResponse,
    MobileRepairGuidanceRequest,
    MobileRepairGuidanceResponse,
    MobileRepairGuidanceStepResponse,
    MobileRuntimeDiagnosticRequest,
    MobileRuntimeDiagnosticResponse,
    MobileRuntimeDiagnosticsPreferenceChangeRequest,
    MobileRuntimeDiagnosticsPreferenceResponse,
    MobileRuntimePrivacyGuardPolicyRequest,
    MobileRuntimePrivacyGuardPolicyResponse,
    MobileRuntimeReleaseCheckRequest,
    MobileRuntimeReleaseCheckResponse,
    MobileTimelineItemResponse,
    MobileTimelineRequest,
    MobileTimelineResponse,
    MobileTodayCheckinResponse,
    MobileTodayRequest,
    MobileTodayResponse,
    MobileTodayTaskSummaryResponse,
    MobileWeeklySummaryRequest,
    MobileWeeklySummaryResponse,
)
from app.services import checkin_visibility as visibility
from app.services.checkin_visibility import DEFAULT_SCOPE
from app.services.relationship_intelligence import record_relationship_event
from app.services.timeline_archive import (
    build_archive_cursor,
    ensure_checkin_archive_fields,
    list_archive_checkins,
)
from app.services.upload_access import (
    actor_can_reference_upload,
    resolve_upload_file_path,
    to_client_upload_url,
)

router = APIRouter(prefix="/mobile", tags=["移动端"])

SERVICE_TERMS_VERSION = "2026-09-01"
PRIVACY_POLICY_VERSION = "2026-09-01"
SAFETY_HANDOFF_MESSAGE = "这条内容里可能有需要优先照顾自己的部分，先看安全支持与官方求助资源，再决定要不要记录或发送。"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_demo_user(user: User) -> bool:
    from app.api.deps import DEMO_USER_ID

    return str(user.id) == str(DEMO_USER_ID)


def _client_request_id_of(checkin: Checkin) -> str | None:
    context = checkin.client_context if isinstance(checkin.client_context, dict) else {}
    value = context.get("client_request_id")
    return str(value) if value else None


def _state_version(*, user_id: uuid.UUID, pair_ids: list[str], latest: datetime | None) -> str:
    raw = "|".join([str(user_id), *sorted(pair_ids), latest.isoformat() if latest else ""])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


async def _active_pairs(db: AsyncSession, user: User) -> list[Pair]:
    result = await db.execute(
        select(Pair).where(
            Pair.status == PairStatus.ACTIVE,
            (Pair.user_a_id == user.id) | (Pair.user_b_id == user.id),
        )
    )
    return list(result.scalars().all())


async def _latest_checkin_at(db: AsyncSession, user: User) -> datetime | None:
    result = await db.execute(
        select(Checkin.created_at)
        .where(Checkin.user_id == user.id)
        .order_by(Checkin.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── 预检 / 启动 / 今日 ──


@router.post("/preflight", response_model=MobileClientPreflightResponse)
async def mobile_preflight(req: MobileClientPreflightRequest) -> MobileClientPreflightResponse:
    """客户端能力预检：只返回公开协议版本与登录方式，不接触任何私有数据。"""
    return MobileClientPreflightResponse(
        client_type=req.client_type,
        service_terms_version=SERVICE_TERMS_VERSION,
        privacy_policy_version=PRIVACY_POLICY_VERSION,
        login_methods=[
            MobileClientLoginMethodResponse(method="wechat", enabled=True),
            MobileClientLoginMethodResponse(method="password", enabled=True),
        ],
    )


@router.post("/bootstrap", response_model=MobileBootstrapResponse)
async def mobile_bootstrap(
    req: MobileBootstrapRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileBootstrapResponse:
    pairs = await _active_pairs(db, user)
    latest = await _latest_checkin_at(db, user)
    state_version = _state_version(
        user_id=user.id, pair_ids=[str(pair.id) for pair in pairs], latest=latest
    )
    if req.known_state_version and req.known_state_version == state_version:
        return MobileBootstrapResponse(
            state_version=state_version,
            not_modified=True,
            server_time=_now(),
        )

    relationships = [
        MobileBootstrapRelationshipResponse(
            space_id=pair.id,
            relationship_type=str(getattr(pair.type, "value", pair.type)),
            title=None,
            role="member",
            member_count=2 if (pair.user_a_id and pair.user_b_id) else 1,
        )
        for pair in pairs
    ]
    return MobileBootstrapResponse(
        state_version=state_version,
        server_time=_now(),
        account=MobileBootstrapAccountResponse(
            user_id=user.id,
            nickname=str(user.nickname or ""),
            wechat_bound=bool(getattr(user, "wechat_openid", None)),
        ),
        relationships=relationships,
        notifications=MobileBootstrapNotificationsResponse(
            delivery_channel="app_push",
            delivery_available=False,
            delivery_reason_code="provider_unconfigured",
        ),
        realtime_voice=MobileBootstrapRealtimeVoiceResponse(
            available=False,
            reason_code="provider_unconfigured",
            fallback_action="use_voice_upload",
        ),
    )


@router.post("/today", response_model=MobileTodayResponse)
async def mobile_today(
    req: MobileTodayRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileTodayResponse:
    today = current_local_date()
    pair: Pair | None = None
    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin).where(
            Checkin.user_id == user.id,
            Checkin.checkin_date == today,
            Checkin.pair_id == (pair.id if pair else None),
        )
    )
    mine = result.scalar_one_or_none()

    partner_done: bool | None = None
    if pair is not None:
        partner_result = await db.execute(
            select(Checkin).where(
                Checkin.pair_id == pair.id,
                Checkin.user_id != user.id,
                Checkin.checkin_date == today,
            )
        )
        partner_done = partner_result.scalar_one_or_none() is not None

    latest = await _latest_checkin_at(db, user)
    state_version = _state_version(
        user_id=user.id,
        pair_ids=[str(pair.id)] if pair else [],
        latest=latest,
    )
    if req.known_state_version and req.known_state_version == state_version:
        return MobileTodayResponse(
            scope=req.scope,
            relationship_space_id=pair.id if pair else None,
            relationship_ready=pair is not None,
            date=str(today),
            state_version=state_version,
            not_modified=True,
        )

    return MobileTodayResponse(
        scope=req.scope,
        relationship_space_id=pair.id if pair else None,
        relationship_ready=pair is not None,
        date=str(today),
        state_version=state_version,
        checkin=MobileTodayCheckinResponse(
            my_completed=mine is not None,
            partner_completed=partner_done,
            both_completed=(mine is not None and bool(partner_done)) if pair else None,
            can_submit=mine is None,
            submitted_at=mine.created_at if mine else None,
        ),
        tasks=MobileTodayTaskSummaryResponse(),
    )


# ── 打卡与可见性 ──


@router.post("/checkins", response_model=MobileCheckinCreateResponse)
async def mobile_create_checkin(
    req: MobileCheckinCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinCreateResponse:
    if _is_demo_user(user):
        raise HTTPException(status_code=403, detail="公用样例账号不能写入记录")

    pair: Pair | None = None
    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    content = str(req.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="记录内容不能为空")

    scope = visibility.normalize_scope(req.visibility_scope or DEFAULT_SCOPE)
    if scope in visibility.PARTNER_VISIBLE_SCOPES:
        if not req.sharing_confirmed:
            raise HTTPException(status_code=422, detail="共享前必须显式确认")
        if pair is None:
            raise HTTPException(status_code=422, detail="单人记录没有可共享的对象")
    elif pair is None and scope == visibility.SHARED_ORIGINAL:
        raise HTTPException(status_code=422, detail="单人记录没有可共享的对象")

    today = current_local_date()
    existing = (
        await db.execute(
            select(Checkin).where(
                Checkin.user_id == user.id,
                Checkin.checkin_date == today,
                Checkin.pair_id == (pair.id if pair else None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if _client_request_id_of(existing) == req.client_request_id:
            return MobileCheckinCreateResponse(
                record_id=existing.id,
                scope=req.scope,
                relationship_space_id=existing.pair_id,
                checkin_date=existing.checkin_date,
                deduplicated=True,
                visibility_scope=str(existing.visibility_scope or DEFAULT_SCOPE),
            )
        raise HTTPException(status_code=409, detail="今天已经记录过了")

    context = req.client_context.model_dump() if req.client_context else {}
    context["client_request_id"] = req.client_request_id
    risk_level = str((context.get("risk_level") or "none")).lower()
    safety_mode = risk_level == "high"

    checkin = Checkin(
        pair_id=pair.id if pair else None,
        user_id=user.id,
        content=content,
        image_url=req.image_url,
        voice_url=req.voice_url,
        mood_tags={"tags": req.mood_tags} if req.mood_tags else None,
        client_context=context,
        mood_score=req.mood_score,
        checkin_date=today,
        visibility_scope=scope,
        visibility_version=1,
        sharing_confirmed_at=_now() if scope in visibility.PARTNER_VISIBLE_SCOPES else None,
        visibility_updated_at=None,
    )
    db.add(checkin)
    await db.flush()
    ensure_checkin_archive_fields(checkin)
    await db.commit()
    await db.refresh(checkin)

    return MobileCheckinCreateResponse(
        record_id=checkin.id,
        scope=req.scope,
        relationship_space_id=checkin.pair_id,
        checkin_date=checkin.checkin_date,
        visibility_scope=scope,
        processing_status="safety_handoff" if safety_mode else "queued",
        safety_mode=safety_mode,
        safety_handoff=SAFETY_HANDOFF_MESSAGE if safety_mode else None,
    )


async def _load_readable_checkin(
    db: AsyncSession, record_id: uuid.UUID, user: User
) -> tuple[Checkin, bool]:
    checkin = await db.get(Checkin, record_id)
    if checkin is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if str(checkin.user_id) == str(user.id):
        return checkin, True
    if checkin.pair_id is not None and visibility.is_partner_visible(
        str(checkin.visibility_scope or DEFAULT_SCOPE)
    ):
        pair = await db.get(Pair, checkin.pair_id)
        if pair is not None and str(user.id) in (str(pair.user_a_id), str(pair.user_b_id)):
            return checkin, False
    raise HTTPException(status_code=404, detail="记录不存在")


@router.post("/checkins/detail", response_model=MobileCheckinDetailResponse)
async def mobile_checkin_detail(
    req: MobileCheckinDetailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinDetailResponse:
    checkin, is_owner = await _load_readable_checkin(db, req.record_id, user)
    scope = str(checkin.visibility_scope or DEFAULT_SCOPE)
    public_scope = visibility.PRIVATE if scope == visibility.SYSTEM_ONLY else scope
    detail_version = str(int(checkin.visibility_version or 1))

    if req.known_detail_version and req.known_detail_version == detail_version:
        return MobileCheckinDetailResponse(
            record_id=checkin.id,
            relationship_space_id=checkin.pair_id,
            is_owner=is_owner,
            visibility_scope=public_scope,
            detail_version=detail_version,
            not_modified=True,
        )

    archive_insight = ensure_checkin_archive_fields(checkin)

    if is_owner and scope != visibility.SYSTEM_ONLY:
        return MobileCheckinDetailResponse(
            record_id=checkin.id,
            relationship_space_id=checkin.pair_id,
            is_owner=True,
            visibility_scope=public_scope,
            content=checkin.content,
            image_url=checkin.image_url,
            voice_url=checkin.voice_url,
            mood_tags=list((checkin.mood_tags or {}).get("tags") or []),
            title=str(archive_insight.get("title") or ""),
            summary=str(archive_insight.get("summary") or ""),
            tags=list(archive_insight.get("tags") or []),
            detail_version=detail_version,
        )

    projection = visibility.build_partner_projection(archive_insight)
    return MobileCheckinDetailResponse(
        record_id=checkin.id,
        relationship_space_id=checkin.pair_id,
        is_owner=is_owner,
        visibility_scope=public_scope,
        title=projection["title"],
        summary=projection["summary"],
        tags=projection["tags"],
        locked_reason="原文和原媒体默认仅记录者本人可见。",
        detail_version=detail_version,
    )


@router.post("/checkins/visibility", response_model=MobileCheckinVisibilityResponse)
async def mobile_checkin_visibility(
    req: MobileCheckinVisibilityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinVisibilityResponse:
    checkin = await db.get(Checkin, req.record_id)
    if checkin is None or str(checkin.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="记录不存在")
    payload = visibility.serialize_visibility(
        checkin, actor_user_id=user.id, known_version=req.known_version
    )
    return MobileCheckinVisibilityResponse(**payload)


@router.post("/checkins/visibility/change", response_model=MobileCheckinVisibilityChangeResponse)
async def mobile_change_checkin_visibility(
    req: MobileCheckinVisibilityChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinVisibilityChangeResponse:
    payload = await visibility.change_visibility(
        db,
        record_id=req.record_id,
        actor_user_id=user.id,
        expected_version=req.expected_version,
        target_scope=req.visibility_scope,
        sharing_confirmed=req.sharing_confirmed,
        client_request_id=req.client_request_id,
    )
    await db.commit()
    return MobileCheckinVisibilityChangeResponse(**payload)


# ── 改写预演（只能复制，不能替用户发送）──


def _safety_category(risk_level: str) -> str:
    return "threat" if str(risk_level or "").lower() in {"high", "severe"} else "normal"


@router.post("/communication/simulations", response_model=MobileMessageSimulationResponse)
async def mobile_simulate_message(
    req: MobileMessageSimulationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMessageSimulationResponse:
    pair: Pair | None = None
    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    result = await simulate_message(
        MessageSimulationRequest(draft=req.draft),
        pair_id=pair.id if pair else None,
        user=user,
        db=db,
    )
    risk_level = str(result.risk_level or "medium").lower()
    return MobileMessageSimulationResponse(
        simulation_id=str(result.event_id or ""),
        scope=req.scope,
        relationship_space_id=pair.id if pair else None,
        structured_result=MessageSimulationStructuredResult(
            original_intent=str(result.conversation_goal or "把这件事说清楚"),
            received_meaning=str(result.partner_view or ""),
            risks=list(result.avoid_list or []),
            rewrite=str(result.safer_rewrite or req.draft),
            boundaries=list(result.do_list or []),
            safety_category=_safety_category(risk_level),
        ),
        safety_mode=risk_level in {"high", "severe"},
        safety_handoff=result.safety_handoff,
    )


@router.post(
    "/communication/simulations/feedback",
    response_model=MobileMessageSimulationFeedbackResponse,
)
async def mobile_simulation_feedback(
    req: MobileMessageSimulationFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMessageSimulationFeedbackResponse:
    result = await submit_message_decision_feedback(
        str(req.simulation_id),
        DecisionFeedbackRequest(feedback_type=req.feedback_type, note=req.note),
        user=user,
        db=db,
    )
    return MobileMessageSimulationFeedbackResponse(
        simulation_id=req.simulation_id,
        feedback_status=str(result.get("feedback_type") or req.feedback_type),
    )


# ── 实时语音票据 ──


@router.post("/realtime-voice/tickets", response_model=MobileRealtimeVoiceTicketResponse)
async def mobile_realtime_voice_ticket(
    req: MobileRealtimeVoiceTicketRequest,
    user: User = Depends(get_current_user),
) -> MobileRealtimeVoiceTicketResponse:
    return MobileRealtimeVoiceTicketResponse(
        ticket=create_realtime_ws_ticket(str(user.id)),
        expires_in=max(30, int(settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS)),
    )


# ── 时间轴 ──


@router.post("/timeline", response_model=MobileTimelineResponse)
async def mobile_timeline(
    req: MobileTimelineRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileTimelineResponse:
    pair: Pair | None = None
    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    rows = await list_archive_checkins(
        db,
        pair_id=str(pair.id) if pair else None,
        user_id=None if pair else str(user.id),
        limit=req.limit + 1,
    )

    items: list[MobileTimelineItemResponse] = []
    for checkin in rows:
        is_mine = str(checkin.user_id) == str(user.id)
        scope_value = str(checkin.visibility_scope or DEFAULT_SCOPE)
        if not is_mine and not visibility.is_partner_visible(scope_value):
            # private 的伴侣记录不出现（不泄露存在性）
            continue
        insight = ensure_checkin_archive_fields(checkin)
        if is_mine:
            title = str(insight.get("title") or "留下一条今天的记录")
            summary = str(insight.get("summary") or "")
            item_scope = "private" if scope_value == visibility.PRIVATE else scope_value
            kind = "my_record"
        else:
            projection = visibility.build_partner_projection(insight)
            title = projection["title"]
            summary = projection["summary"]
            item_scope = "shared_summary"
            kind = "partner_summary"
        items.append(
            MobileTimelineItemResponse(
                item_id=str(checkin.id),
                kind=kind,
                occurred_at=checkin.created_at,
                local_date=str(checkin.checkin_date),
                title=title,
                summary=summary,
                visibility_scope=item_scope,
                is_mine=is_mine,
                can_manage_visibility=is_mine,
                original_available=is_mine,
                ai_generated=True,
            )
        )

    has_more = len(items) > req.limit
    visible = items[: req.limit]
    page_version = hashlib.sha256(
        "|".join(f"{item.item_id}:{item.visibility_scope}" for item in visible).encode("utf-8")
    ).hexdigest()[:32]
    if req.known_page_version and req.known_page_version == page_version:
        return MobileTimelineResponse(
            scope=req.scope,
            relationship_space_id=pair.id if pair else None,
            page_version=page_version,
            not_modified=True,
        )

    next_cursor = None
    if has_more and visible:
        last = next(
            (row for row in rows if str(row.id) == visible[-1].item_id), None
        )
        if last is not None:
            next_cursor = build_archive_cursor(last.created_at, [last.id])

    return MobileTimelineResponse(
        scope=req.scope,
        relationship_space_id=pair.id if pair else None,
        page_version=page_version,
        item_count=len(visible),
        items=visible,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# ── 媒体分阶段上传（一律私有暂存）──

MEDIA_ALLOWED_TYPES = {
    "image": {"image/jpeg", "image/png", "image/webp", "image/gif"},
    "voice": {
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "audio/webm",
        "audio/mp4",
        "audio/aac",
    },
}
MEDIA_SUBDIR = {"image": "images", "voice": "voices"}


def _normalize_content_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _media_storage_path(media_id: str) -> str:
    parts = [part for part in str(media_id or "").split("/") if part]
    if (
        len(parts) != 2
        or parts[0] not in ("images", "voices")
        or not parts[1]
        or ".." in parts[1]
    ):
        raise HTTPException(status_code=404, detail="媒体不存在")
    return f"/uploads/{parts[0]}/{parts[1]}"


@router.post("/media/preflight", response_model=MobileMediaPreflightResponse)
async def mobile_media_preflight(
    req: MobileMediaPreflightRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaPreflightResponse:
    content_type = _normalize_content_type(req.content_type)
    if content_type not in MEDIA_ALLOWED_TYPES[req.media_kind]:
        raise HTTPException(status_code=400, detail="不支持的媒体格式")
    if req.size_bytes > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)",
        )
    if req.relationship_space_id is not None:
        await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    ticket = create_media_upload_ticket(
        user_id=str(user.id),
        media_kind=req.media_kind,
        content_type=content_type,
        size_bytes=req.size_bytes,
        client_request_id=req.client_request_id,
    )
    expires_at = _now() + timedelta(seconds=MEDIA_UPLOAD_TICKET_TTL_SECONDS)

    session = (
        await db.execute(
            select(MobileMediaUpload).where(
                MobileMediaUpload.user_id == user.id,
                MobileMediaUpload.client_request_id == req.client_request_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        session = MobileMediaUpload(
            user_id=user.id,
            client_request_id=req.client_request_id,
            media_kind=req.media_kind,
            content_type=content_type,
            size_bytes=req.size_bytes,
            status="ready",
            expires_at=expires_at,
        )
        db.add(session)
    else:
        session.media_kind = req.media_kind
        session.content_type = content_type
        session.size_bytes = req.size_bytes
        session.status = "ready"
        session.expires_at = expires_at
    session.updated_at = _now()
    await db.commit()

    return MobileMediaPreflightResponse(
        upload_ticket=ticket,
        media_kind=req.media_kind,
        content_type=content_type,
        size_bytes=req.size_bytes,
        expires_at=expires_at,
        expires_in=MEDIA_UPLOAD_TICKET_TTL_SECONDS,
        max_size_bytes=settings.MAX_FILE_SIZE,
    )


@router.post("/media/upload", response_model=MobileMediaUploadResponse)
async def mobile_media_upload(
    file: UploadFile = File(...),
    upload_ticket: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaUploadResponse:
    claims = decode_media_upload_ticket(upload_ticket)
    if not claims or str(claims.get("sub")) != str(user.id):
        raise HTTPException(status_code=403, detail="上传票据无效或已过期")
    kind = str(claims.get("media_kind") or "")
    if kind not in MEDIA_ALLOWED_TYPES:
        raise HTTPException(status_code=403, detail="上传票据无效或已过期")

    content_type = _normalize_content_type(file.content_type)
    if content_type != str(claims.get("content_type")):
        raise HTTPException(status_code=400, detail="上传内容与预检声明不一致")
    if content_type not in MEDIA_ALLOWED_TYPES[kind]:
        raise HTTPException(status_code=400, detail="不支持的媒体格式")

    payload = await _save_file(file, MEDIA_SUBDIR[kind], db=db, actor_user_id=user.id)
    media_id = f"{MEDIA_SUBDIR[kind]}/{payload['filename']}"

    request_id = str(claims.get("req") or "")
    if request_id:
        session = (
            await db.execute(
                select(MobileMediaUpload).where(
                    MobileMediaUpload.user_id == user.id,
                    MobileMediaUpload.client_request_id == request_id,
                )
            )
        ).scalar_one_or_none()
        if session is not None:
            session.status = "uploaded"
            session.media_id = media_id
            session.updated_at = _now()
    await db.commit()
    return MobileMediaUploadResponse(
        media_id=media_id,
        media_kind=kind,
        content_type=content_type,
        size_bytes=int(payload["size"]),
        access_url=str(payload["access_url"]),
    )


@router.post("/media/access", response_model=MobileMediaAccessResponse)
async def mobile_media_access(
    req: MobileMediaAccessRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaAccessResponse:
    storage_path = _media_storage_path(req.media_id)
    if not await actor_can_reference_upload(db, storage_path, actor_user_id=user.id):
        raise HTTPException(status_code=404, detail="媒体不存在")
    access_url = to_client_upload_url(storage_path)
    if not access_url:
        raise HTTPException(status_code=404, detail="媒体不存在")
    return MobileMediaAccessResponse(media_id=req.media_id, access_url=access_url)


@router.post("/media/discard", response_model=MobileMediaDiscardResponse)
async def mobile_media_discard(
    req: MobileMediaDiscardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaDiscardResponse:
    storage_path = _media_storage_path(req.media_id)
    if not await actor_can_reference_upload(db, storage_path, actor_user_id=user.id):
        raise HTTPException(status_code=404, detail="媒体不存在")

    file_removed = False
    try:
        resolved = resolve_upload_file_path(storage_path)
    except ValueError:
        resolved = None
    if resolved and os.path.exists(resolved):
        os.remove(resolved)
        file_removed = True

    removed = await db.execute(
        delete(UploadAsset).where(UploadAsset.storage_path == storage_path)
    )
    grants_removed = int(removed.rowcount or 0)
    await db.commit()
    return MobileMediaDiscardResponse(
        media_id=req.media_id,
        discarded_at=_now(),
        file_removed=file_removed,
        upload_grants_removed=grants_removed,
    )


# ── 记录修正 / 删除 ──


async def _owned_checkin(db: AsyncSession, record_id: uuid.UUID, user: User) -> Checkin:
    checkin = await db.get(Checkin, record_id, with_for_update=True)
    if checkin is None or str(checkin.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return checkin


def _detail_version(checkin: Checkin) -> str:
    return str(int(checkin.visibility_version or 1))


def _conflict(current_version: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": "记录已被更新，请刷新后重试", "version": current_version},
    )


@router.post("/checkins/correct", response_model=MobileCheckinCorrectionResponse)
async def mobile_correct_checkin(
    req: MobileCheckinCorrectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinCorrectionResponse:
    checkin = await _owned_checkin(db, req.record_id, user)
    current_version = _detail_version(checkin)
    if str(req.expected_detail_version) != current_version:
        raise _conflict(current_version)

    corrected_fields: list[str] = []
    if req.content is not None:
        content = str(req.content).strip()
        if not content:
            raise HTTPException(status_code=422, detail="记录内容不能为空")
        checkin.content = content
        corrected_fields.append("content")
    if req.mood_score is not None:
        checkin.mood_score = req.mood_score
        corrected_fields.append("mood_score")
    if req.mood_tags is not None:
        checkin.mood_tags = {"tags": req.mood_tags} if req.mood_tags else None
        corrected_fields.append("mood_tags")
    if not corrected_fields:
        raise HTTPException(status_code=422, detail="没有需要修正的字段")

    # 内容变化会让既有派生结果失真，必须失效
    counts = await visibility.invalidate_derived_artifacts(db, checkin)

    # 重新生成归档摘要，避免旧摘要与新内容不一致
    context = checkin.client_context if isinstance(checkin.client_context, dict) else {}
    context.pop("archive_insight", None)
    checkin.client_context = context
    checkin.archive_title = None
    checkin.archive_summary = None
    checkin.archive_tags = None
    ensure_checkin_archive_fields(checkin)

    checkin.visibility_version = int(checkin.visibility_version or 1) + 1
    checkin.visibility_updated_at = _now()
    await db.commit()

    return MobileCheckinCorrectionResponse(
        record_id=checkin.id,
        detail_version=_detail_version(checkin),
        corrected_at=_now(),
        corrected_fields=corrected_fields,
        visibility_scope=str(checkin.visibility_scope or DEFAULT_SCOPE),
        **counts,
    )


@router.post("/checkins/delete", response_model=MobileCheckinDeleteResponse)
async def mobile_delete_checkin(
    req: MobileCheckinDeleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinDeleteResponse:
    checkin = await _owned_checkin(db, req.record_id, user)
    current_version = _detail_version(checkin)
    if str(req.expected_detail_version) != current_version:
        raise _conflict(current_version)

    counts = await visibility.invalidate_derived_artifacts(db, checkin)

    media_removed = 0
    for upload_path in (checkin.image_url, checkin.voice_url):
        if not upload_path:
            continue
        try:
            resolved = resolve_upload_file_path(upload_path)
        except ValueError:
            resolved = None
        if resolved and os.path.exists(resolved):
            os.remove(resolved)
            media_removed += 1
        await db.execute(delete(UploadAsset).where(UploadAsset.storage_path == upload_path))

    # 撤回共享并清除原文/原媒体：删除即不可再读
    checkin.visibility_scope = visibility.PRIVATE
    checkin.sharing_confirmed_at = None
    checkin.image_url = None
    checkin.voice_url = None
    checkin.content = ""
    checkin.raw_deleted_at = _now()
    checkin.visibility_version = int(checkin.visibility_version or 1) + 1
    checkin.visibility_updated_at = _now()
    await db.commit()

    return MobileCheckinDeleteResponse(
        record_id=checkin.id,
        deleted_at=_now(),
        media_removed=media_removed,
        **counts,
    )


# ── 通知 ──


async def _unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    rows = (
        await db.execute(
            select(UserNotification.id).where(
                UserNotification.user_id == user_id,
                UserNotification.is_read.is_(False),
            )
        )
    ).scalars().all()
    return len(rows)


@router.post("/notifications/list", response_model=MobileNotificationListResponse)
async def mobile_notifications_list(
    req: MobileNotificationListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNotificationListResponse:
    stmt = select(UserNotification).where(UserNotification.user_id == user.id)
    if req.unread_only:
        stmt = stmt.where(UserNotification.is_read.is_(False))
    if req.cursor_before is not None:
        stmt = stmt.where(UserNotification.created_at < req.cursor_before)
    stmt = stmt.order_by(UserNotification.created_at.desc()).limit(req.limit + 1)
    rows = list((await db.execute(stmt)).scalars().all())

    has_more = len(rows) > req.limit
    visible = rows[: req.limit]
    next_cursor = (
        visible[-1].created_at.isoformat() if has_more and visible else None
    )
    return MobileNotificationListResponse(
        items=[
            MobileNotificationItemResponse(
                notification_id=row.id,
                notification_type=str(row.type or "notice"),
                content=str(row.content or ""),
                target_path=row.target_path,
                is_read=bool(row.is_read),
                created_at=row.created_at,
            )
            for row in visible
        ],
        next_cursor=next_cursor,
        unread_count=await _unread_count(db, user.id),
    )


@router.post("/notifications/read", response_model=MobileNotificationReadResponse)
async def mobile_notifications_read(
    req: MobileNotificationReadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNotificationReadResponse:
    result = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.user_id == user.id,
            UserNotification.id.in_(req.notification_ids),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return MobileNotificationReadResponse(
        updated_count=int(result.rowcount or 0),
        unread_count=await _unread_count(db, user.id),
    )


@router.post("/notifications/read-all", response_model=MobileNotificationReadResponse)
async def mobile_notifications_read_all(
    req: MobileNotificationReadAllRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNotificationReadResponse:
    result = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.user_id == user.id,
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return MobileNotificationReadResponse(
        updated_count=int(result.rowcount or 0),
        unread_count=await _unread_count(db, user.id),
    )


# ── 周报摘要 ──


@router.post("/reports/weekly-summary", response_model=MobileWeeklySummaryResponse)
async def mobile_weekly_summary(
    req: MobileWeeklySummaryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileWeeklySummaryResponse:
    pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)

    report = (
        await db.execute(
            select(Report)
            .where(Report.pair_id == pair.id, Report.type == ReportType.WEEKLY)
            .order_by(Report.report_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if report is None:
        return MobileWeeklySummaryResponse(
            relationship_space_id=pair.id,
            status="not_available",
            summary_version="none",
        )

    summary_version = hashlib.sha256(
        f"{report.id}:{report.status}:{report.report_date}".encode("utf-8")
    ).hexdigest()[:32]
    if req.known_summary_version and req.known_summary_version == summary_version:
        return MobileWeeklySummaryResponse(
            relationship_space_id=pair.id,
            status=_report_status(report),
            summary_version=summary_version,
            not_modified=True,
        )

    content = report.content if isinstance(report.content, dict) else {}
    return MobileWeeklySummaryResponse(
        relationship_space_id=pair.id,
        status=_report_status(report),
        summary_version=summary_version,
        report_date=report.report_date,
        generated_at=report.created_at,
        trend=_trend_of(content),
        summary=_text_of(content, "summary") or _text_of(content, "overview"),
        highlights=_list_of(content, "highlights"),
        actions=_list_of(content, "actions") or _list_of(content, "suggestions"),
        encouragement=_text_of(content, "encouragement"),
        limitation_note="周报为聚合结果，不含任何一方原文。",
        ai_generated=True,
        full_report_available=False,
    )


def _report_status(report: Report) -> str:
    status_value = str(getattr(report.status, "value", report.status) or "")
    if status_value == ReportStatus.COMPLETED.value:
        return "ready" if report.content else "pending"
    if status_value == ReportStatus.FAILED.value:
        return "failed"
    return "pending"


def _text_of(content: dict, key: str) -> str | None:
    value = content.get(key)
    text = str(value).strip() if value is not None else ""
    return text or None


def _list_of(content: dict, key: str) -> list[str]:
    value = content.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _trend_of(content: dict) -> str | None:
    value = str(content.get("trend") or "").strip().lower()
    return value if value in {"improving", "stable", "declining", "unknown"} else None


# ── 媒体状态 / 取消 ──


@router.post("/media/status", response_model=MobileMediaStatusResponse)
async def mobile_media_status(
    req: MobileMediaStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaStatusResponse:
    session = (
        await db.execute(
            select(MobileMediaUpload).where(
                MobileMediaUpload.user_id == user.id,
                MobileMediaUpload.client_request_id == req.client_request_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    status_value = str(session.status or "ready")
    if status_value in {"ready", "uploaded"} and session.expires_at <= _now():
        status_value = "expired"
        session.status = "expired"
        await db.commit()

    return MobileMediaStatusResponse(
        client_request_id=session.client_request_id,
        status=status_value,
        media_id=session.media_id,
        expires_at=session.expires_at,
        upload_required=status_value == "ready",
    )


@router.post("/media/cancel", response_model=MobileMediaCancelResponse)
async def mobile_media_cancel(
    req: MobileMediaCancelRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileMediaCancelResponse:
    claims = decode_media_upload_ticket(req.upload_ticket)
    if not claims or str(claims.get("sub")) != str(user.id):
        raise HTTPException(status_code=403, detail="上传票据无效或已过期")

    request_id = str(claims.get("req") or "")
    deduplicated = False
    if request_id:
        session = (
            await db.execute(
                select(MobileMediaUpload).where(
                    MobileMediaUpload.user_id == user.id,
                    MobileMediaUpload.client_request_id == request_id,
                )
            )
        ).scalar_one_or_none()
        if session is not None:
            deduplicated = session.status == "cancelled"
            session.status = "cancelled"
            session.updated_at = _now()
    await db.commit()
    return MobileMediaCancelResponse(cancelled_at=_now(), deduplicated=deduplicated)


# ── 行动任务 ──


def _action_payload(task: RelationshipTask, pair_id: uuid.UUID) -> MobileActionItemResponse:
    return MobileActionItemResponse(
        action_id=task.id,
        relationship_space_id=pair_id,
        title=str(task.title or ""),
        category=str(task.category or "activity"),
        target_scope="both" if task.user_id is None else "self",
        importance_level=str(
            getattr(task.importance_level, "value", task.importance_level) or "medium"
        ),
        status=str(getattr(task.status, "value", task.status) or "pending"),
        due_date=task.due_date,
        completed_at=task.completed_at,
    )


@router.post("/actions", response_model=list[MobileActionItemResponse])
async def mobile_actions(
    req: MobileActionListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MobileActionItemResponse]:
    pair: Pair | None = None
    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)
    if pair is None:
        return []

    stmt = select(RelationshipTask).where(RelationshipTask.pair_id == pair.id)
    if req.status:
        stmt = stmt.where(RelationshipTask.status == TaskStatus(req.status))
    stmt = stmt.order_by(RelationshipTask.due_date.asc()).limit(50)
    rows = list((await db.execute(stmt)).scalars().all())
    return [_action_payload(task, pair.id) for task in rows]


@router.post("/actions/complete", response_model=MobileActionItemResponse)
async def mobile_complete_action(
    req: MobileActionCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileActionItemResponse:
    pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)
    task = await db.get(RelationshipTask, req.action_id, with_for_update=True)
    if task is None or str(task.pair_id) != str(pair.id):
        raise HTTPException(status_code=404, detail="行动不存在")

    if task.status != TaskStatus.COMPLETED:
        task.status = TaskStatus.COMPLETED
        task.completed_at = _now()
        await db.commit()
    payload = _action_payload(task, pair.id)
    payload.deduplicated = False
    return payload


@router.post("/actions/feedback", response_model=MobileActionFeedbackResponse)
async def mobile_action_feedback(
    req: MobileActionFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileActionFeedbackResponse:
    pair = await validate_pair_access(req.relationship_space_id, user, db, require_active=True)
    task = await db.get(RelationshipTask, req.action_id)
    if task is None or str(task.pair_id) != str(pair.id):
        raise HTTPException(status_code=404, detail="行动不存在")

    payload = {
        "action_id": str(task.id),
        "usefulness_score": req.usefulness_score,
        "friction_score": req.friction_score,
        "relationship_shift_score": req.relationship_shift_score,
        "note": req.note,
    }
    event = await record_relationship_event(
        db,
        event_type="mobile.action.feedback",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="relationship_task",
        entity_id=task.id,
        payload=payload,
        idempotency_key=f"mobile-action-feedback:{task.id}:{user.id}",
    )
    await db.commit()
    feedback_version = hashlib.sha256(
        f"{task.id}:{event.id}".encode("utf-8")
    ).hexdigest()[:32]
    return MobileActionFeedbackResponse(
        action_id=task.id,
        relationship_space_id=pair.id,
        submitted_at=_now(),
        feedback_version=feedback_version,
    )


# ── 运行时策略 ──

PRIVACY_GUARD_POLICY_VERSION = "v1"
APP_RELEASE_POLICY_VERSION = "v1"


@router.post("/runtime/privacy-guard-policy", response_model=MobileRuntimePrivacyGuardPolicyResponse)
async def mobile_privacy_guard_policy(
    req: MobileRuntimePrivacyGuardPolicyRequest,
) -> MobileRuntimePrivacyGuardPolicyResponse:
    biometric_ok = req.biometric_state == "enrolled"
    if biometric_ok:
        unlock_method = "biometric"
    elif req.device_credential_available:
        unlock_method = "device_credential"
    else:
        unlock_method = "unavailable"

    access_mode = "full" if unlock_method != "unavailable" else "restricted"
    return MobileRuntimePrivacyGuardPolicyResponse(
        access_mode=access_mode,
        unlock_method=unlock_method,
        device_credential_fallback_available=req.device_credential_available,
        screen_capture_policy=(
            "block" if req.screen_capture_protection_supported else "obscure_and_warn"
        ),
        sensitive_views_available=access_mode == "full",
        policy_version=PRIVACY_GUARD_POLICY_VERSION,
    )


@router.post("/runtime/release-check", response_model=MobileRuntimeReleaseCheckResponse)
async def mobile_release_check(
    req: MobileRuntimeReleaseCheckRequest,
) -> MobileRuntimeReleaseCheckResponse:
    minimum_version = str(getattr(settings, "MOBILE_MIN_APP_VERSION", "") or "")
    minimum_build = int(getattr(settings, "MOBILE_MIN_APP_BUILD", 0) or 0)
    latest_version = str(getattr(settings, "MOBILE_LATEST_APP_VERSION", "") or "")
    latest_build = int(getattr(settings, "MOBILE_LATEST_APP_BUILD", 0) or 0)
    update_url = str(getattr(settings, "MOBILE_UPDATE_URL", "") or "") or None

    policy_ready = bool(minimum_version) and minimum_build > 0
    if not policy_ready:
        return MobileRuntimeReleaseCheckResponse(
            status="policy_unavailable",
            policy_ready=False,
            next_action="none",
            minimum_version="0.0.0",
            minimum_build=0,
            latest_version=req.app_version,
            latest_build=req.build_number,
            message="更新策略尚未配置，继续使用当前版本。",
        )

    below_minimum = (req.app_version, req.build_number) < (minimum_version, minimum_build)
    update_available = latest_build > req.build_number
    if below_minimum:
        return MobileRuntimeReleaseCheckResponse(
            status="update_required",
            update_available=update_available,
            update_required=True,
            policy_ready=True,
            next_action="open_update_url" if update_url else "retry_later",
            reason_code=None if update_url else "update_url_unconfigured",
            minimum_version=minimum_version,
            minimum_build=minimum_build,
            latest_version=latest_version or minimum_version,
            latest_build=latest_build or minimum_build,
            update_url=update_url,
            message="当前版本已低于最低支持版本，请更新后再继续使用。",
        )
    if update_available:
        return MobileRuntimeReleaseCheckResponse(
            status="update_available",
            update_available=True,
            policy_ready=True,
            next_action="open_update_url" if update_url else "none",
            reason_code=None if update_url else "update_url_unconfigured",
            minimum_version=minimum_version,
            minimum_build=minimum_build,
            latest_version=latest_version,
            latest_build=latest_build,
            update_url=update_url,
            message="有新版本可用，建议在方便时更新。",
        )
    return MobileRuntimeReleaseCheckResponse(
        status="supported",
        policy_ready=True,
        minimum_version=minimum_version,
        minimum_build=minimum_build,
        latest_version=latest_version or req.app_version,
        latest_build=latest_build or req.build_number,
        update_url=update_url,
        message="当前版本受支持。",
    )


# ── 通知偏好（存于用户偏好，不新建表）──

NOTIFICATION_CATEGORIES = (
    "task_reminder",
    "relationship_activity",
    "milestone",
    "safety_support",
    "product_update",
)
NOTIFICATION_PREFS_KEY = "mobile_notification_preferences"


def _default_notification_preference(category: str) -> dict:
    return {
        "category": category,
        "enabled": True,
        "in_app_enabled": True,
        "wechat_subscription_enabled": False,
        "app_push_enabled": False,
        "quiet_hours": {"enabled": False, "start": None, "end": None},
        "daily_limit": 5,
        "subscription_state": "unsubscribed",
    }


def _notification_prefs(user: User) -> dict:
    prefs = user.product_prefs if isinstance(user.product_prefs, dict) else {}
    stored = prefs.get(NOTIFICATION_PREFS_KEY)
    result: dict[str, dict] = {}
    for category in NOTIFICATION_CATEGORIES:
        base = _default_notification_preference(category)
        if isinstance(stored, dict) and isinstance(stored.get(category), dict):
            base.update(stored[category])
            base["category"] = category
        result[category] = base
    return result


def _preference_version(entry: dict) -> str:
    raw = "|".join(
        [
            str(entry.get("enabled")),
            str(entry.get("in_app_enabled")),
            str(entry.get("daily_limit")),
            str((entry.get("quiet_hours") or {}).get("enabled")),
            str(entry.get("subscription_state")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _to_preference_response(entry: dict) -> MobileNotificationPreferenceResponse:
    quiet = entry.get("quiet_hours") if isinstance(entry.get("quiet_hours"), dict) else {}
    return MobileNotificationPreferenceResponse(
        category=entry["category"],
        enabled=bool(entry.get("enabled", True)),
        in_app_enabled=bool(entry.get("in_app_enabled", True)),
        wechat_subscription_enabled=bool(entry.get("wechat_subscription_enabled", False)),
        app_push_enabled=bool(entry.get("app_push_enabled", False)),
        quiet_hours=MobileNotificationQuietHours(
            enabled=bool(quiet.get("enabled", False)),
            start=quiet.get("start"),
            end=quiet.get("end"),
        ),
        daily_limit=int(entry.get("daily_limit", 5)),
        subscription_state=str(entry.get("subscription_state") or "unsubscribed"),
        preference_version=_preference_version(entry),
    )


@router.post(
    "/notification-preferences/status",
    response_model=MobileNotificationPreferencesStatusResponse,
)
async def mobile_notification_preferences_status(
    user: User = Depends(get_current_user),
) -> MobileNotificationPreferencesStatusResponse:
    entries = _notification_prefs(user)
    return MobileNotificationPreferencesStatusResponse(
        preferences=[_to_preference_response(entries[name]) for name in NOTIFICATION_CATEGORIES]
    )


@router.post(
    "/notification-preferences/change",
    response_model=MobileNotificationPreferenceMutationResponse,
)
async def mobile_notification_preference_change(
    req: MobileNotificationPreferenceChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNotificationPreferenceMutationResponse:
    db_user = await db.get(User, user.id)
    if db_user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    entries = _notification_prefs(db_user)
    entry = entries[req.category]
    if req.base_version != _preference_version(entry):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "通知偏好已被更新，请刷新后重试", "version": _preference_version(entry)},
        )

    if req.enabled is not None:
        entry["enabled"] = req.enabled
    if req.in_app_enabled is not None:
        entry["in_app_enabled"] = req.in_app_enabled
    if req.daily_limit is not None:
        entry["daily_limit"] = req.daily_limit
    if req.quiet_hours is not None:
        entry["quiet_hours"] = req.quiet_hours.model_dump()

    prefs = db_user.product_prefs if isinstance(db_user.product_prefs, dict) else {}
    stored = prefs.get(NOTIFICATION_PREFS_KEY)
    if not isinstance(stored, dict):
        stored = {}
    # 赋新对象，避免 JSON 原地修改不被 SQLAlchemy 识别为脏数据
    db_user.product_prefs = {
        **prefs,
        NOTIFICATION_PREFS_KEY: {**stored, req.category: dict(entry)},
    }
    await db.commit()

    return MobileNotificationPreferenceMutationResponse(
        preference=_to_preference_response(entry)
    )


@router.post(
    "/notification-preferences/subscription",
    response_model=MobileNotificationPreferenceMutationResponse,
)
async def mobile_notification_preference_subscription(
    req: MobileNotificationPreferenceSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNotificationPreferenceMutationResponse:
    db_user = await db.get(User, user.id)
    if db_user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    entries = _notification_prefs(db_user)
    entry = entries[req.category]
    if req.base_version != _preference_version(entry):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "通知偏好已被更新，请刷新后重试", "version": _preference_version(entry)},
        )

    entry["subscription_state"] = "unsubscribed" if req.action == "unsubscribe" else "active"
    entry["wechat_subscription_enabled"] = req.action == "resubscribe"

    prefs = db_user.product_prefs if isinstance(db_user.product_prefs, dict) else {}
    stored = prefs.get(NOTIFICATION_PREFS_KEY)
    if not isinstance(stored, dict):
        stored = {}
    db_user.product_prefs = {
        **prefs,
        NOTIFICATION_PREFS_KEY: {**stored, req.category: dict(entry)},
    }
    await db.commit()
    return MobileNotificationPreferenceMutationResponse(
        preference=_to_preference_response(entry)
    )


# ── 运行时诊断 ──

DIAGNOSTICS_PREFS_KEY = "mobile_runtime_diagnostics_enabled"


@router.post("/runtime/diagnostics", response_model=MobileRuntimeDiagnosticResponse)
async def mobile_runtime_diagnostic(
    req: MobileRuntimeDiagnosticRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileRuntimeDiagnosticResponse:
    if not req.diagnostics_consent:
        return MobileRuntimeDiagnosticResponse(
            accepted=False,
            reason="diagnostics_consent_required",
        )

    payload = {
        "event_type": req.event_type,
        "platform": req.platform,
        "app_version": req.app_version,
        "build_number": req.build_number,
        "occurred_at": req.occurred_at.isoformat(),
        "crash_fingerprint_sha256": req.crash_fingerprint_sha256,
        "metric_name": req.metric_name,
        "metric_value": req.metric_value,
        "network_type": req.network_type,
        "app_state": req.app_state,
    }
    idempotency_key = f"mobile-diagnostic:{user.id}:{req.client_event_id}"
    existing = (
        await db.execute(
            select(RelationshipEvent.id).where(
                RelationshipEvent.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()

    event = await record_relationship_event(
        db,
        event_type="mobile.runtime.diagnostic",
        user_id=user.id,
        entity_type="runtime_diagnostic",
        payload=payload,
        idempotency_key=idempotency_key,
    )
    await db.commit()
    return MobileRuntimeDiagnosticResponse(
        accepted=True,
        deduplicated=existing is not None,
        diagnostic_id=str(event.id),
    )


@router.post(
    "/runtime/diagnostics-preference/status",
    response_model=MobileRuntimeDiagnosticsPreferenceResponse,
)
async def mobile_diagnostics_preference_status(
    user: User = Depends(get_current_user),
) -> MobileRuntimeDiagnosticsPreferenceResponse:
    prefs = user.product_prefs if isinstance(user.product_prefs, dict) else {}
    return MobileRuntimeDiagnosticsPreferenceResponse(
        diagnostics_enabled=bool(prefs.get(DIAGNOSTICS_PREFS_KEY, False))
    )


@router.post(
    "/runtime/diagnostics-preference/change",
    response_model=MobileRuntimeDiagnosticsPreferenceResponse,
)
async def mobile_diagnostics_preference_change(
    req: MobileRuntimeDiagnosticsPreferenceChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileRuntimeDiagnosticsPreferenceResponse:
    db_user = await db.get(User, user.id)
    if db_user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    prefs = db_user.product_prefs if isinstance(db_user.product_prefs, dict) else {}
    db_user.product_prefs = {**prefs, DIAGNOSTICS_PREFS_KEY: req.diagnostics_enabled}
    await db.commit()
    return MobileRuntimeDiagnosticsPreferenceResponse(
        diagnostics_enabled=req.diagnostics_enabled
    )


# ── 打卡媒体变更 ──


@router.post("/checkins/media/change", response_model=MobileCheckinMediaChangeResponse)
async def mobile_checkin_media_change(
    req: MobileCheckinMediaChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileCheckinMediaChangeResponse:
    checkin = await _owned_checkin(db, req.record_id, user)
    current_version = _detail_version(checkin)
    if str(req.expected_detail_version) != current_version:
        raise _conflict(current_version)

    attribute = "image_url" if req.media_kind == "image" else "voice_url"
    previous = getattr(checkin, attribute)
    media_files_removed = 0

    if req.operation in {"remove", "replace"} and previous:
        try:
            resolved = resolve_upload_file_path(previous)
        except ValueError:
            resolved = None
        if resolved and os.path.exists(resolved):
            os.remove(resolved)
            media_files_removed += 1
        await db.execute(delete(UploadAsset).where(UploadAsset.storage_path == previous))
        setattr(checkin, attribute, None)

    new_media_id: str | None = None
    if req.operation in {"attach", "replace"}:
        if not req.replacement_media_id:
            raise HTTPException(status_code=422, detail="缺少替换媒体")
        storage_path = _media_storage_path(req.replacement_media_id)
        if not await actor_can_reference_upload(db, storage_path, actor_user_id=user.id):
            raise HTTPException(status_code=404, detail="媒体不存在")
        setattr(checkin, attribute, storage_path)
        new_media_id = req.replacement_media_id

    counts = await visibility.invalidate_derived_artifacts(db, checkin)
    checkin.visibility_version = int(checkin.visibility_version or 1) + 1
    checkin.visibility_updated_at = _now()
    await db.commit()

    return MobileCheckinMediaChangeResponse(
        record_id=checkin.id,
        detail_version=_detail_version(checkin),
        changed_at=_now(),
        media_kind=req.media_kind,
        operation=req.operation,
        media_id=new_media_id,
        visibility_scope=str(checkin.visibility_scope or DEFAULT_SCOPE),
        access_revoked=bool(previous),
        media_files_removed=media_files_removed,
        **counts,
    )


# ── 修复引导 ──


@router.post("/communication/repair-guidance", response_model=MobileRepairGuidanceResponse)
async def mobile_repair_guidance(
    req: MobileRepairGuidanceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileRepairGuidanceResponse:
    from app.api.v1.crisis import get_repair_protocol, get_solo_repair_protocol

    if req.scope == "relationship":
        if not req.relationship_space_id:
            raise HTTPException(status_code=422, detail="缺少关系空间")
        pair = await validate_pair_access(
            req.relationship_space_id, user, db, require_active=True
        )
        protocol = await get_repair_protocol(pair.id, user=user, db=db)
        space_id = pair.id
    else:
        protocol = await get_solo_repair_protocol(mode="solo", user=user, db=db)
        space_id = None

    guidance_version = hashlib.sha256(
        f"{protocol.protocol_type}:{protocol.level}:{protocol.title}".encode("utf-8")
    ).hexdigest()[:32]
    if req.known_guidance_version and req.known_guidance_version == guidance_version:
        return MobileRepairGuidanceResponse(
            scope=req.scope,
            relationship_space_id=space_id,
            guidance_version=guidance_version,
            not_modified=True,
        )

    return MobileRepairGuidanceResponse(
        scope=req.scope,
        relationship_space_id=space_id,
        guidance_version=guidance_version,
        protocol_type=protocol.protocol_type,
        title=protocol.title,
        summary=protocol.summary,
        timing_hint=protocol.timing_hint,
        steps=[
            MobileRepairGuidanceStepResponse(
                sequence=step.sequence,
                title=step.title,
                action=step.action,
                why=step.why,
                duration_hint=step.duration_hint,
            )
            for step in protocol.steps
        ],
        do_not=list(protocol.do_not or []),
        success_signal=protocol.success_signal,
        escalation_rule=protocol.escalation_rule,
        clinical_disclaimer=protocol.clinical_disclaimer,
        limitation_note=protocol.limitation_note,
        safety_mode=bool(protocol.safety_handoff),
        safety_handoff=protocol.safety_handoff,
        ai_generated=False,
    )


# ── 离线草稿（仅私有，绝不上共享域）──


def _draft_metadata(draft: MobileOfflineDraft, *, deduplicated: bool = False) -> dict:
    return {
        "relationship_space_id": draft.relationship_space_id,
        "revision": int(draft.revision or 1),
        "status": str(draft.status or "active"),
        "visibility_scope": "private",
        "payload_hash": draft.payload_hash,
        "local_updated_at": draft.local_updated_at,
        "server_updated_at": draft.server_updated_at,
        "deduplicated": deduplicated,
    }


async def _owned_draft(
    db: AsyncSession, user: User, client_draft_id: str
) -> MobileOfflineDraft | None:
    return (
        await db.execute(
            select(MobileOfflineDraft).where(
                MobileOfflineDraft.user_id == user.id,
                MobileOfflineDraft.client_draft_id == client_draft_id,
            )
        )
    ).scalar_one_or_none()


@router.post("/offline-drafts/sync", response_model=MobileOfflineDraftMetadataResponse)
async def mobile_offline_draft_sync(
    req: MobileOfflineDraftSyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftMetadataResponse:
    if req.draft.relationship_space_id is not None:
        await validate_pair_access(
            req.draft.relationship_space_id, user, db, require_active=True
        )
    payload = req.draft.model_dump(mode="json")
    payload_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    draft = await _owned_draft(db, user, req.client_draft_id)
    if draft is None:
        if req.base_revision not in (0, 1):
            raise _conflict("0")
        draft = MobileOfflineDraft(
            user_id=user.id,
            client_draft_id=req.client_draft_id,
            relationship_space_id=req.draft.relationship_space_id,
            revision=1,
            status="active",
            visibility_scope="private",
            payload_hash=payload_hash,
            payload=payload,
            local_updated_at=req.local_updated_at,
            server_updated_at=_now(),
        )
        db.add(draft)
        await db.commit()
        return MobileOfflineDraftMetadataResponse(**_draft_metadata(draft))

    if draft.status == "discarded":
        raise HTTPException(status_code=409, detail="草稿已丢弃")
    if int(req.base_revision) != int(draft.revision or 1):
        raise _conflict(str(draft.revision or 1))

    deduplicated = draft.payload_hash == payload_hash
    if not deduplicated:
        draft.revision = int(draft.revision or 1) + 1
        draft.relationship_space_id = req.draft.relationship_space_id
        draft.payload_hash = payload_hash
        draft.payload = payload
        draft.local_updated_at = req.local_updated_at
        draft.server_updated_at = _now()
        await db.commit()
    return MobileOfflineDraftMetadataResponse(
        **_draft_metadata(draft, deduplicated=deduplicated)
    )


@router.post("/offline-drafts/pull", response_model=MobileOfflineDraftDetailResponse)
async def mobile_offline_draft_pull(
    req: MobileOfflineDraftPullRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftDetailResponse:
    draft = await _owned_draft(db, user, req.client_draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="草稿不存在")
    payload = draft.payload if isinstance(draft.payload, dict) else None
    return MobileOfflineDraftDetailResponse(
        **_draft_metadata(draft),
        draft=MobileOfflineDraftPayload(**payload) if payload else None,
    )


@router.post("/offline-drafts/recover", response_model=MobileOfflineDraftDetailResponse)
async def mobile_offline_draft_recover(
    req: MobileOfflineDraftRecoverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftDetailResponse:
    return await mobile_offline_draft_pull(
        MobileOfflineDraftPullRequest(client_draft_id=req.client_draft_id),
        user=user,
        db=db,
    )


@router.post("/offline-drafts/list", response_model=MobileOfflineDraftListResponse)
async def mobile_offline_draft_list(
    req: MobileOfflineDraftListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftListResponse:
    stmt = select(MobileOfflineDraft).where(
        MobileOfflineDraft.user_id == user.id,
        MobileOfflineDraft.status == "active",
    )
    if req.relationship_space_id is not None:
        stmt = stmt.where(
            MobileOfflineDraft.relationship_space_id == req.relationship_space_id
        )
    rows = list(
        (await db.execute(stmt.order_by(MobileOfflineDraft.server_updated_at.desc())))
        .scalars()
        .all()
    )
    return MobileOfflineDraftListResponse(
        drafts=[MobileOfflineDraftMetadataResponse(**_draft_metadata(row)) for row in rows]
    )


@router.post("/offline-drafts/discard", response_model=MobileOfflineDraftMetadataResponse)
async def mobile_offline_draft_discard(
    req: MobileOfflineDraftDiscardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftMetadataResponse:
    draft = await _owned_draft(db, user, req.client_draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="草稿不存在")
    if draft.status == "discarded":
        return MobileOfflineDraftMetadataResponse(
            **_draft_metadata(draft, deduplicated=True)
        )
    if int(req.base_revision) != int(draft.revision or 1):
        raise _conflict(str(draft.revision or 1))

    draft.status = "discarded"
    draft.payload = None
    draft.payload_hash = None
    draft.revision = int(draft.revision or 1) + 1
    draft.server_updated_at = _now()
    await db.commit()
    return MobileOfflineDraftMetadataResponse(**_draft_metadata(draft))


@router.post("/offline-drafts/adopt", response_model=MobileOfflineDraftDetailResponse)
async def mobile_offline_draft_adopt(
    req: MobileOfflineDraftAdoptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileOfflineDraftDetailResponse:
    draft = await _owned_draft(db, user, req.client_draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="草稿不存在")
    if draft.status != "active":
        raise HTTPException(status_code=409, detail="草稿已丢弃")
    if int(req.base_revision) != int(draft.revision or 1):
        raise _conflict(str(draft.revision or 1))

    payload = draft.payload if isinstance(draft.payload, dict) else {}
    draft.status = "discarded"
    draft.revision = int(draft.revision or 1) + 1
    draft.server_updated_at = _now()
    await db.commit()
    return MobileOfflineDraftDetailResponse(
        **_draft_metadata(draft),
        draft=MobileOfflineDraftPayload(**payload) if payload else None,
    )


# ── 推送注册 ──


def _push_status_payload(
    registration: MobilePushRegistration | None, *, deduplicated: bool = False
) -> dict:
    if registration is None:
        return {
            "registration_state": "unregistered",
            "permission_state": "unknown",
            "next_action": "register",
            "deduplicated": deduplicated,
        }
    registration_state = str(registration.registration_state or "unregistered")
    permission_state = str(registration.permission_state or "unknown")
    if registration_state == "active":
        next_action = "none"
    elif permission_state in {"denied", "not_determined"}:
        next_action = "request_permission"
    else:
        next_action = "register"
    return {
        "registration_state": registration_state,
        "permission_state": permission_state,
        "revocation_reason": registration.revocation_reason,
        "next_action": next_action,
        "deduplicated": deduplicated,
    }


async def _owned_push_registration(
    db: AsyncSession, user: User, installation_id: str
) -> MobilePushRegistration | None:
    return (
        await db.execute(
            select(MobilePushRegistration).where(
                MobilePushRegistration.user_id == user.id,
                MobilePushRegistration.installation_id == installation_id,
            )
        )
    ).scalar_one_or_none()


@router.post("/push/status", response_model=PushRegistrationStatusResponse)
async def mobile_push_status(
    req: PushRegistrationStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushRegistrationStatusResponse:
    registration = await _owned_push_registration(db, user, req.installation_id)
    return PushRegistrationStatusResponse(**_push_status_payload(registration))


@router.post("/push/permission-sync", response_model=PushRegistrationStatusResponse)
async def mobile_push_permission_sync(
    req: PushPermissionSyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushRegistrationStatusResponse:
    registration = await _owned_push_registration(db, user, req.installation_id)
    if registration is None:
        registration = MobilePushRegistration(
            user_id=user.id,
            installation_id=req.installation_id,
            platform=req.platform,
            provider=req.provider,
            permission_state=req.permission_state,
            registration_state="unregistered",
        )
        db.add(registration)
    else:
        registration.permission_state = req.permission_state
        registration.platform = req.platform
        registration.provider = req.provider
    if req.permission_state in {"denied", "not_determined"}:
        registration.registration_state = "unregistered"
    registration.updated_at = _now()
    await db.commit()
    return PushRegistrationStatusResponse(**_push_status_payload(registration))


@router.post("/push/receipts", response_model=PushReceiptResponse)
async def mobile_push_receipt(
    req: PushReceiptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushReceiptResponse:
    occurred_at = req.occurred_at or _now()
    idempotency_key = (
        f"mobile-push-receipt:{user.id}:{req.installation_id}:{req.receipt_type}:"
        f"{occurred_at.isoformat()}"
    )
    existing = (
        await db.execute(
            select(RelationshipEvent.id).where(
                RelationshipEvent.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    await record_relationship_event(
        db,
        event_type="mobile.push.receipt",
        user_id=user.id,
        entity_type="push_receipt",
        payload={
            "installation_id": req.installation_id,
            "receipt_type": req.receipt_type,
            "occurred_at": occurred_at.isoformat(),
        },
        idempotency_key=idempotency_key,
    )
    await db.commit()
    return PushReceiptResponse(deduplicated=existing is not None)


# ── 对齐洞察 ──


@router.post("/communication/alignment", response_model=MobileNarrativeAlignmentResponse)
async def mobile_narrative_alignment(
    req: MobileNarrativeAlignmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNarrativeAlignmentResponse:
    pair = await validate_pair_access(
        req.relationship_space_id, user, db, require_active=True
    )
    event = (
        await db.execute(
            select(RelationshipEvent)
            .where(
                RelationshipEvent.pair_id == pair.id,
                RelationshipEvent.event_type == "alignment.generated",
            )
            .order_by(RelationshipEvent.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if event is None:
        return MobileNarrativeAlignmentResponse(
            relationship_space_id=pair.id,
            status="not_available",
            alignment_version="none",
        )

    payload = event.payload if isinstance(event.payload, dict) else {}
    alignment_version = hashlib.sha256(str(event.id).encode("utf-8")).hexdigest()[:32]
    if req.known_alignment_version and req.known_alignment_version == alignment_version:
        return MobileNarrativeAlignmentResponse(
            relationship_space_id=pair.id,
            alignment_id=str(event.id),
            status="ready",
            alignment_version=alignment_version,
            not_modified=True,
        )

    confidence = payload.get("confidence")
    source = str(payload.get("source") or "").strip().lower()
    return MobileNarrativeAlignmentResponse(
        relationship_space_id=pair.id,
        alignment_id=str(event.id),
        status="ready",
        alignment_version=alignment_version,
        shared_story=_text_of(payload, "shared_story") or _text_of(payload, "summary"),
        my_view_summary=_text_of(payload, "my_view_summary"),
        partner_view_summary=_text_of(payload, "partner_view_summary"),
        misread_risk=_text_of(payload, "misread_risk"),
        divergence_points=_list_of(payload, "divergence_points")
        or _list_of(payload, "divergent_points"),
        bridge_actions=_list_of(payload, "bridge_actions") or _list_of(payload, "suggestions"),
        suggested_opening=_text_of(payload, "suggested_opening"),
        confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
        history_sufficiency=_text_of(payload, "history_sufficiency"),
        limitation_note="对齐结果基于双方已共享的记录聚合，不含任何一方原文。",
        generated_at=event.created_at,
        source="fallback" if source == "fallback" else ("ai" if source else None),
        ai_generated=True,
        ai_disclosure="这段对齐由 AI 辅助生成，可能有偏差，请以你们自己的感受为准。",
    )


@router.post(
    "/communication/alignment/feedback",
    response_model=MobileNarrativeAlignmentFeedbackResponse,
)
async def mobile_narrative_alignment_feedback(
    req: MobileNarrativeAlignmentFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MobileNarrativeAlignmentFeedbackResponse:
    pair = await validate_pair_access(
        req.relationship_space_id, user, db, require_active=True
    )
    try:
        alignment_uuid = uuid.UUID(str(req.alignment_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="无效的对齐结果 ID")

    target = await db.get(RelationshipEvent, alignment_uuid)
    if (
        target is None
        or str(target.pair_id) != str(pair.id)
        or target.event_type != "alignment.generated"
    ):
        raise HTTPException(status_code=404, detail="对齐结果不存在")

    idempotency_key = f"mobile-alignment-feedback:{target.id}:{user.id}"
    existing = (
        await db.execute(
            select(RelationshipEvent.id).where(
                RelationshipEvent.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    event = await record_relationship_event(
        db,
        event_type="mobile.alignment.feedback",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="alignment_result",
        entity_id=target.id,
        payload={"alignment_id": str(target.id), "feedback_type": req.feedback_type, "note": req.note},
        idempotency_key=idempotency_key,
    )
    await db.commit()
    feedback_version = hashlib.sha256(
        f"{target.id}:{event.id}".encode("utf-8")
    ).hexdigest()[:32]
    return MobileNarrativeAlignmentFeedbackResponse(
        alignment_id=str(target.id),
        feedback_type=req.feedback_type,
        feedback_label=ALIGNMENT_FEEDBACK_LABELS.get(req.feedback_type, "已记录"),
        feedback_version=feedback_version,
        deduplicated=existing is not None,
        submitted_at=_now(),
    )


ALIGNMENT_FEEDBACK_LABELS = {
    "accurate": "说得准",
    "missed_my_view": "漏掉了我的视角",
    "missed_partner_view": "漏掉了对方的视角",
    "not_helpful": "帮助不大",
}

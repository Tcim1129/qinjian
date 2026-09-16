"""配对系统接口"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.core.config import settings
from app.core.database import get_db
from app.core.time import current_local_date
from app.core.invite_codes import (
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    generate_invite_code as _generate_invite_code,
    normalize_invite_code,
)
from app.models import (
    Pair,
    PairChangeRequest,
    PairChangeRequestKind,
    PairChangeRequestMessage,
    PairChangeRequestPhase,
    PairChangeRequestResolutionReason,
    PairChangeRequestStatus,
    PairStatus,
    PairType,
    RelationshipEvent,
    User,
    UserNotification,
)
from app.schemas import (
    PairBreakMessageRequest,
    PairBreakRequest,
    PairBreakRetentionDecisionRequest,
    PairBreakRetentionRequest,
    PairChangeDecisionRequest,
    PairChangeRequestMessageResponse,
    PairChangeRequestBundleResponse,
    PairChangeRequestResponse,
    PairCreateRequest,
    PairJoinPreviewResponse,
    PairJoinRequest,
    PairJoinSubmitRequest,
    PairTaskPlannerSettingsRequest,
    PairTaskPlannerSettingsResponse,
    PairResponse,
    PairSummaryResponse,
    PairUpdateTypeRequest,
    UpdatePartnerNicknameRequest,
)
from app.services.display_labels import pair_type_label, status_label
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.relationship_intelligence import record_relationship_event
from app.services.test_accounts import is_relaxed_test_account
from app.services.task_planner import (
    merge_pair_task_planner_overrides,
    reset_unstarted_system_tasks,
    resolve_effective_task_planner_settings,
    resolve_pair_task_planner_overrides,
)

router = APIRouter(prefix="/pairs", tags=["配对"])


PAIR_CHANGE_KIND_LABELS = {
    PairChangeRequestKind.JOIN_REQUEST.value: "加入关系",
    PairChangeRequestKind.TYPE_CHANGE.value: "切换关系类型",
    PairChangeRequestKind.BREAK_REQUEST.value: "断绝关系",
}
BREAK_REQUEST_CHOICE_WINDOW = timedelta(hours=24)
BREAK_REQUEST_RETENTION_WINDOW = timedelta(hours=12)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _relationship_detail_path(pair_id: str | uuid.UUID) -> str:
    return f"/relationship-space/{pair_id}"


def _change_kind_label(value: PairChangeRequestKind | str | None) -> str:
    normalized = value.value if hasattr(value, "value") else str(value or "").strip()
    return PAIR_CHANGE_KIND_LABELS.get(normalized, "关系确认")


def _change_request_status_label(request: PairChangeRequest) -> str:
    if request.kind != PairChangeRequestKind.BREAK_REQUEST:
        return status_label(request.status.value)

    if request.status == PairChangeRequestStatus.PENDING:
        if request.phase == PairChangeRequestPhase.AWAITING_TIMEOUT:
            return "倒计时中"
        if request.phase == PairChangeRequestPhase.AWAITING_RETENTION_CHOICE:
            return "待对方决定"
        if request.phase == PairChangeRequestPhase.RETAINING:
            return "挽留中"
        return "处理中"
    if request.status == PairChangeRequestStatus.APPROVED:
        return "已断绝"
    if request.status == PairChangeRequestStatus.REJECTED:
        return "已恢复"
    if request.status == PairChangeRequestStatus.CANCELLED:
        return "已撤回"
    return status_label(request.status.value)


def _is_waiting_for_me(request: PairChangeRequest, me: User | None) -> bool:
    if not me or request.status != PairChangeRequestStatus.PENDING:
        return False

    me_id = str(me.id)
    if request.kind != PairChangeRequestKind.BREAK_REQUEST:
        return str(request.approver_user_id) == me_id

    if request.phase == PairChangeRequestPhase.AWAITING_RETENTION_CHOICE:
        return str(request.approver_user_id) == me_id
    if request.phase == PairChangeRequestPhase.RETAINING:
        return str(request.requester_user_id) == me_id
    return False


async def _build_change_request_messages_response(
    db: AsyncSession, request: PairChangeRequest
) -> list[PairChangeRequestMessageResponse]:
    result = await db.execute(
        select(PairChangeRequestMessage)
        .where(PairChangeRequestMessage.request_id == request.id)
        .order_by(PairChangeRequestMessage.created_at.asc())
    )
    messages = result.scalars().all()
    responses: list[PairChangeRequestMessageResponse] = []
    for item in messages:
        sender = await db.get(User, item.sender_user_id)
        responses.append(
            PairChangeRequestMessageResponse(
                id=item.id,
                sender_user_id=item.sender_user_id,
                sender_nickname=sender.nickname if sender else None,
                message=item.message,
                created_at=item.created_at,
            )
        )
    return responses


async def _get_pending_change_request(
    db: AsyncSession, pair_id: str | uuid.UUID
) -> PairChangeRequest | None:
    result = await db.execute(
        select(PairChangeRequest)
        .where(
            PairChangeRequest.pair_id == pair_id,
            PairChangeRequest.status == PairChangeRequestStatus.PENDING,
        )
        .order_by(PairChangeRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _generate_unique_invite_code(db: AsyncSession) -> str:
    invite_code = _generate_invite_code()
    for _ in range(4):
        existing = await db.execute(select(Pair.id).where(Pair.invite_code == invite_code))
        if not existing.scalar_one_or_none():
            return invite_code
        invite_code = _generate_invite_code()
    raise HTTPException(status_code=503, detail="邀请码生成繁忙，请稍后重试")


async def _get_latest_change_request(
    db: AsyncSession, pair_id: str | uuid.UUID
) -> PairChangeRequest | None:
    result = await db.execute(
        select(PairChangeRequest)
        .where(PairChangeRequest.pair_id == pair_id)
        .order_by(PairChangeRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _build_change_request_response(
    db: AsyncSession,
    request: PairChangeRequest | None,
    *,
    me: User | None = None,
) -> PairChangeRequestResponse | None:
    if not request:
        return None

    requester = await db.get(User, request.requester_user_id)
    approver = await db.get(User, request.approver_user_id)
    messages = await _build_change_request_messages_response(db, request)

    return PairChangeRequestResponse(
        id=request.id,
        pair_id=request.pair_id,
        kind=request.kind.value,
        kind_label=_change_kind_label(request.kind),
        status=request.status.value,
        status_label=_change_request_status_label(request),
        requested_type=request.requested_type.value if request.requested_type else None,
        requested_type_label=pair_type_label(
            request.requested_type.value if request.requested_type else None
        ),
        requester_user_id=request.requester_user_id,
        requester_nickname=requester.nickname if requester else None,
        approver_user_id=request.approver_user_id,
        approver_nickname=approver.nickname if approver else None,
        requested_by_me=bool(me and str(request.requester_user_id) == str(me.id)),
        waiting_for_me=_is_waiting_for_me(request, me),
        allow_retention=bool(request.allow_retention),
        phase=request.phase.value if request.phase else None,
        expires_at=request.expires_at,
        resolution_reason=(
            request.resolution_reason.value if request.resolution_reason else None
        ),
        messages=messages,
        created_at=request.created_at,
        decided_at=request.decided_at,
    )


async def _build_pair_response(
    db: AsyncSession,
    pair: Pair,
    me: User,
    partner: User | None = None,
) -> PairResponse:
    data = PairResponse.model_validate(pair).model_dump()
    data["type_label"] = pair_type_label(data.get("type"))
    data["status_label"] = status_label(data.get("status"))
    if partner:
        is_user_a = str(pair.user_a_id) == str(me.id)
        custom_nickname = (
            pair.custom_partner_nickname_a
            if is_user_a
            else pair.custom_partner_nickname_b
        )

        data.update(
            {
                "partner_id": partner.id,
                "partner_nickname": partner.nickname,
                "partner_avatar": partner.wechat_avatar or partner.avatar_url,
                "partner_email": partner.email,
                "partner_phone": partner.phone,
                "custom_partner_nickname": custom_nickname,
            }
        )

    pending_request = await _get_pending_change_request(db, pair.id)
    latest_request = await _get_latest_change_request(db, pair.id)
    data["pending_change_request"] = await _build_change_request_response(
        db, pending_request, me=me
    )
    data["latest_change_request"] = await _build_change_request_response(
        db, latest_request, me=me
    )
    return PairResponse(**data)


async def _resolve_partner_for_pair(
    db: AsyncSession, pair: Pair, me: User
) -> User | None:
    partner_id = pair.user_b_id if pair.user_a_id == me.id else pair.user_a_id
    return await db.get(User, partner_id) if partner_id else None


async def _build_pair_bundle_response(
    db: AsyncSession,
    *,
    pair: Pair,
    me: User,
    request: PairChangeRequest,
) -> PairChangeRequestBundleResponse:
    partner = await _resolve_partner_for_pair(db, pair, me)
    pair_response = await _build_pair_response(db, pair, me, partner)
    request_response = await _build_change_request_response(db, request, me=me)
    return PairChangeRequestBundleResponse(pair=pair_response, request=request_response)


def _serialize_task_settings_response(
    *,
    pair: Pair,
    user: User,
) -> PairTaskPlannerSettingsResponse:
    overrides = resolve_pair_task_planner_overrides(pair.task_planner_settings)
    effective = resolve_effective_task_planner_settings(
        user.product_prefs,
        pair.task_planner_settings,
    )
    return PairTaskPlannerSettingsResponse(
        pair_id=pair.id,
        overrides=overrides,
        effective_settings=effective,
    )


async def _ensure_no_pending_request(
    db: AsyncSession, pair_id: str | uuid.UUID
) -> None:
    pair = await db.get(Pair, pair_id)
    if pair:
        await _sync_expired_break_requests_for_pair(db, pair)
        if pair.status == PairStatus.ENDED:
            raise HTTPException(status_code=409, detail="这段关系已经结束")
    pending_request = await _get_pending_change_request(db, pair_id)
    if pending_request:
        raise HTTPException(status_code=409, detail="这段关系已经有待确认请求")


async def _notify_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    content: str,
    target_path: str | None = None,
    notification_type: str = "pair_change",
) -> None:
    db.add(
        UserNotification(
            user_id=user_id,
            type=notification_type,
            content=content,
            target_path=target_path,
        )
    )
    await db.flush()


async def _create_change_request_message(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    message: str,
) -> PairChangeRequestMessage:
    item = PairChangeRequestMessage(
        request_id=request_id,
        sender_user_id=sender_user_id,
        message=message.strip(),
    )
    db.add(item)
    await db.flush()
    return item


async def _record_pair_request_event(
    db: AsyncSession,
    *,
    event_type: str,
    pair: Pair,
    actor: User | None,
    request: PairChangeRequest,
    extra_payload: dict | None = None,
) -> RelationshipEvent:
    payload = {
        "request_id": str(request.id),
        "request_kind": request.kind.value,
        "request_kind_label": _change_kind_label(request.kind),
        "request_status": request.status.value,
        "requested_type": request.requested_type.value if request.requested_type else None,
        "requested_type_label": pair_type_label(
            request.requested_type.value if request.requested_type else None
        ),
        "allow_retention": bool(request.allow_retention),
        "phase": request.phase.value if request.phase else None,
        "expires_at": request.expires_at.isoformat() if request.expires_at else None,
        "resolution_reason": (
            request.resolution_reason.value if request.resolution_reason else None
        ),
    }
    if actor:
        payload["actor_user_id"] = str(actor.id)
        payload["actor_nickname"] = actor.nickname
    if extra_payload:
        payload.update(extra_payload)

    return await record_relationship_event(
        db,
        event_type=event_type,
        pair_id=pair.id,
        user_id=actor.id if actor else None,
        entity_type="pair_change_request",
        entity_id=request.id,
        source="system",
        payload=payload,
        idempotency_key=f"{event_type}:{request.id}",
    )


async def _sync_expired_break_request(
    db: AsyncSession,
    *,
    pair: Pair,
    request: PairChangeRequest,
) -> bool:
    if (
        request.kind != PairChangeRequestKind.BREAK_REQUEST
        or request.status != PairChangeRequestStatus.PENDING
        or not request.expires_at
    ):
        return False

    now = _utcnow()
    if request.expires_at > now:
        return False

    requester = await db.get(User, request.requester_user_id)
    approver = await db.get(User, request.approver_user_id)
    target_path = _relationship_detail_path(pair.id)

    if request.phase == PairChangeRequestPhase.AWAITING_TIMEOUT:
        request.status = PairChangeRequestStatus.APPROVED
        request.resolution_reason = (
            PairChangeRequestResolutionReason.NO_RETENTION_TIMEOUT
        )
        request.decided_at = now
        pair.status = PairStatus.ENDED
        await _notify_user(
            db,
            user_id=request.requester_user_id,
            content="断绝关系申请已按 24 小时倒计时自动生效，关系现已解除。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=request.approver_user_id,
            content="由于 24 小时已到，这次断绝关系申请已自动生效，关系现已解除。",
            target_path=target_path,
        )
    elif request.phase == PairChangeRequestPhase.AWAITING_RETENTION_CHOICE:
        request.status = PairChangeRequestStatus.APPROVED
        request.resolution_reason = PairChangeRequestResolutionReason.CHOICE_TIMEOUT
        request.decided_at = now
        pair.status = PairStatus.ENDED
        await _notify_user(
            db,
            user_id=request.requester_user_id,
            content="对方在 24 小时内没有选择是否挽留，断绝关系申请已自动生效。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=request.approver_user_id,
            content="你在 24 小时内没有回应，这次关系已按断绝申请自动解除。",
            target_path=target_path,
        )
    elif request.phase == PairChangeRequestPhase.RETAINING:
        request.status = PairChangeRequestStatus.APPROVED
        request.resolution_reason = PairChangeRequestResolutionReason.RETENTION_TIMEOUT
        request.decided_at = now
        pair.status = PairStatus.ENDED
        await _notify_user(
            db,
            user_id=request.requester_user_id,
            content="挽留阶段已超过 12 小时未完成处理，关系已按断绝申请自动解除。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=request.approver_user_id,
            content="挽留阶段已超过 12 小时未完成处理，这次关系已自动解除。",
            target_path=target_path,
        )
    else:
        return False

    await _record_pair_request_event(
        db,
        event_type="pair.break_completed",
        pair=pair,
        actor=None,
        request=request,
        extra_payload={
            "requester_nickname": requester.nickname if requester else None,
            "approver_nickname": approver.nickname if approver else None,
        },
    )
    return True


async def _sync_expired_break_requests_for_pair(db: AsyncSession, pair: Pair) -> None:
    result = await db.execute(
        select(PairChangeRequest)
        .where(
            PairChangeRequest.pair_id == pair.id,
            PairChangeRequest.kind == PairChangeRequestKind.BREAK_REQUEST,
            PairChangeRequest.status == PairChangeRequestStatus.PENDING,
        )
        .order_by(PairChangeRequest.created_at.desc())
    )
    for request in result.scalars().all():
        await _sync_expired_break_request(db, pair=pair, request=request)


async def _sync_expired_break_requests_for_user(db: AsyncSession, user: User) -> None:
    result = await db.execute(
        select(PairChangeRequest, Pair)
        .join(Pair, Pair.id == PairChangeRequest.pair_id)
        .where(
            PairChangeRequest.kind == PairChangeRequestKind.BREAK_REQUEST,
            PairChangeRequest.status == PairChangeRequestStatus.PENDING,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
        )
        .order_by(PairChangeRequest.created_at.desc())
    )
    for request, pair in result.all():
        await _sync_expired_break_request(db, pair=pair, request=request)


async def _get_pair_for_join_code(
    db: AsyncSession, invite_code: str
) -> Pair:
    normalized_invite_code = normalize_invite_code(invite_code)
    result = await db.execute(
        select(Pair).where(Pair.invite_code == normalized_invite_code)
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    if pair.status == PairStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="这段关系已经建立，邀请码不能重复加入")
    if pair.status == PairStatus.ENDED:
        raise HTTPException(status_code=404, detail="邀请码已失效")
    return pair


async def _get_change_request_for_decision(
    db: AsyncSession,
    *,
    pair_id: str,
    request_id: str,
    user: User,
) -> tuple[Pair, PairChangeRequest]:
    pair = await validate_pair_access(pair_id, user, db, require_active=False)
    await _sync_expired_break_requests_for_pair(db, pair)
    result = await db.execute(
        select(PairChangeRequest).where(PairChangeRequest.pair_id == pair.id)
    )
    change_request = next(
        (
            item
            for item in result.scalars().all()
            if str(item.id) == str(request_id)
        ),
        None,
    )
    if not change_request or str(change_request.pair_id) != str(pair.id):
        raise HTTPException(status_code=404, detail="待确认请求不存在")
    if change_request.status != PairChangeRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="这条请求已经处理过了")
    return pair, change_request


@router.post("/create", response_model=PairResponse)
async def create_pair(
    req: PairCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建或获取一个待邀请关系，直接返回邀请码。"""
    existing_result = await db.execute(
        select(Pair)
        .where(
            Pair.user_a_id == user.id,
            Pair.user_b_id.is_(None),
            Pair.status == PairStatus.PENDING,
        )
        .order_by(Pair.created_at.desc())
        .limit(1)
    )
    existing_pair = existing_result.scalar_one_or_none()
    if existing_pair:
        return await _build_pair_response(db, existing_pair, user)

    invite_code = await _generate_unique_invite_code(db)

    pair = Pair(
        user_a_id=user.id,
        type=None,
        invite_code=invite_code,
        status=PairStatus.PENDING,
    )
    db.add(pair)
    await db.flush()
    return await _build_pair_response(db, pair, user)


@router.post("/{pair_id}/invite-code/refresh", response_model=PairResponse)
async def refresh_pair_invite_code(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """刷新待邀请关系的邀请码，不影响已有待确认申请。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=False)
    if str(pair.user_a_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有邀请发起方可以刷新邀请码")
    if pair.status != PairStatus.PENDING:
        raise HTTPException(status_code=409, detail="当前关系状态不能刷新邀请码")
    await consume_request_cooldown(
        bucket="pair-invite-refresh",
        scope_key=f"{pair.id}:{user.id}",
        window_seconds=settings.PAIR_INVITE_REFRESH_WINDOW_SECONDS,
        max_attempts=settings.PAIR_INVITE_REFRESH_MAX_ATTEMPTS,
        limit_message="邀请码换得太频繁了",
        bypass=is_relaxed_test_account(user),
    )

    pair.invite_code = await _generate_unique_invite_code(db)
    await db.flush()
    partner = await _resolve_partner_for_pair(db, pair, user)
    return await _build_pair_response(db, pair, user, partner)


@router.post("/join/preview", response_model=PairJoinPreviewResponse)
async def preview_join_pair(
    req: PairJoinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """校验邀请码，并返回邀请发起人的基础信息。"""
    pair = await _get_pair_for_join_code(db, req.invite_code)
    if pair.user_a_id == user.id:
        raise HTTPException(status_code=400, detail="不能与自己配对")

    pending_request = await _get_pending_change_request(db, pair.id)
    if pending_request:
        if (
            pending_request.kind == PairChangeRequestKind.JOIN_REQUEST
            and str(pending_request.requester_user_id) == str(user.id)
        ):
            inviter = await db.get(User, pair.user_a_id)
            return PairJoinPreviewResponse(
                pair_id=pair.id,
                invite_code=pair.invite_code,
                inviter_user_id=pair.user_a_id,
                inviter_nickname=inviter.nickname if inviter else None,
                current_status=pair.status.value,
                current_status_label=status_label(pair.status.value),
                pending_request=await _build_change_request_response(
                    db, pending_request, me=user
                ),
            )
        raise HTTPException(status_code=409, detail="这段关系已经有待确认加入请求")

    if pair.user_b_id and str(pair.user_b_id) != str(user.id):
        raise HTTPException(status_code=409, detail="这段关系已经有待确认加入请求")

    inviter = await db.get(User, pair.user_a_id)
    return PairJoinPreviewResponse(
        pair_id=pair.id,
        invite_code=pair.invite_code,
        inviter_user_id=pair.user_a_id,
        inviter_nickname=inviter.nickname if inviter else None,
        current_status=pair.status.value,
        current_status_label=status_label(pair.status.value),
    )


@router.post("/join", response_model=PairChangeRequestBundleResponse)
async def join_pair(
    req: PairJoinSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过邀请码发起加入请求，等待发起方确认后才生效。"""
    pair = await _get_pair_for_join_code(db, req.invite_code)
    if pair.user_a_id == user.id:
        raise HTTPException(status_code=400, detail="不能与自己配对")

    await _ensure_no_pending_request(db, pair.id)
    if pair.user_b_id and str(pair.user_b_id) != str(user.id):
        raise HTTPException(status_code=409, detail="这段关系已经有待确认加入请求")

    requested_type = PairType(req.type)
    pair.user_b_id = user.id
    pair.status = PairStatus.PENDING
    pair.type = None

    change_request = PairChangeRequest(
        pair_id=pair.id,
        kind=PairChangeRequestKind.JOIN_REQUEST,
        status=PairChangeRequestStatus.PENDING,
        requested_type=requested_type,
        requester_user_id=user.id,
        approver_user_id=pair.user_a_id,
    )
    db.add(change_request)
    pair.invite_code = await _generate_unique_invite_code(db)
    await db.flush()

    approver = await db.get(User, pair.user_a_id)
    target_path = _relationship_detail_path(pair.id)
    await _notify_user(
        db,
        user_id=pair.user_a_id,
        content=f"{user.nickname} 申请加入这段关系，并希望按“{pair_type_label(req.type)}”建立，等待你确认。",
        target_path=target_path,
    )
    await _notify_user(
        db,
        user_id=user.id,
        content=f"已把加入请求发给 {approver.nickname if approver else '对方'}，等待对方确认。",
        target_path=target_path,
    )
    await _record_pair_request_event(
        db,
        event_type="pair.join_requested",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={
            "approver_user_id": str(pair.user_a_id),
            "approver_nickname": approver.nickname if approver else None,
        },
    )

    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.get("/me", response_model=list[PairResponse])
async def get_my_pairs(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取当前用户的所有配对。"""
    await _sync_expired_break_requests_for_user(db, user)
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    pairs = result.scalars().all()
    responses: list[PairResponse] = []
    for pair in pairs:
        partner = await _resolve_partner_for_pair(db, pair, user)
        responses.append(await _build_pair_response(db, pair, user, partner))
    return responses


@router.get("/{pair_id}/change-request", response_model=dict)
async def get_pair_change_request_state(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前关系的待处理请求和最近一次处理结果。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=False)
    await _sync_expired_break_requests_for_pair(db, pair)
    pending_request = await _get_pending_change_request(db, pair.id)
    latest_request = await _get_latest_change_request(db, pair.id)
    return {
        "pending_request": await _build_change_request_response(
            db, pending_request, me=user
        ),
        "latest_request": await _build_change_request_response(
            db, latest_request, me=user
        ),
    }


@router.patch("/{pair_id}/type", response_model=PairChangeRequestBundleResponse)
async def request_pair_type_change(
    pair_id: str,
    req: PairUpdateTypeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起关系类型切换请求，等待对方确认后才生效。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    next_type = PairType(req.type)
    if pair.type == next_type:
        raise HTTPException(status_code=400, detail="当前已经是这个关系类型")

    await _ensure_no_pending_request(db, pair.id)

    approver_user_id = pair.user_b_id if pair.user_a_id == user.id else pair.user_a_id
    if not approver_user_id:
        raise HTTPException(status_code=409, detail="这段关系还没有完成建立")

    change_request = PairChangeRequest(
        pair_id=pair.id,
        kind=PairChangeRequestKind.TYPE_CHANGE,
        status=PairChangeRequestStatus.PENDING,
        requested_type=next_type,
        requester_user_id=user.id,
        approver_user_id=approver_user_id,
    )
    db.add(change_request)
    await db.flush()

    approver = await db.get(User, approver_user_id)
    target_path = _relationship_detail_path(pair.id)
    await _notify_user(
        db,
        user_id=approver_user_id,
        content=(
            f"{user.nickname} 希望把关系类型改成“{pair_type_label(req.type)}”，"
            "这可能影响系统判断，等待你确认。"
        ),
        target_path=target_path,
    )
    await _notify_user(
        db,
        user_id=user.id,
        content=f"已发起关系类型切换申请，等待 {approver.nickname if approver else '对方'} 确认。",
        target_path=target_path,
    )
    await _record_pair_request_event(
        db,
        event_type="pair.type_change_requested",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={
            "previous_type": pair.type.value if pair.type else None,
            "previous_type_label": pair_type_label(pair.type.value if pair.type else None),
            "approver_user_id": str(approver_user_id),
            "approver_nickname": approver.nickname if approver else None,
        },
    )

    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/decision",
    response_model=PairChangeRequestBundleResponse,
)
async def decide_pair_change_request(
    pair_id: str,
    request_id: str,
    req: PairChangeDecisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认或拒绝加入/切换请求。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if change_request.kind == PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=409, detail="断绝关系请求请使用专用接口处理")
    if str(change_request.approver_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有待确认方才能处理这条请求")

    requester = await db.get(User, change_request.requester_user_id)
    target_path = _relationship_detail_path(pair.id)

    if req.decision == "approve":
        change_request.status = PairChangeRequestStatus.APPROVED
        change_request.decided_at = _utcnow()

        if change_request.kind == PairChangeRequestKind.JOIN_REQUEST:
            pair.status = PairStatus.ACTIVE
            pair.type = change_request.requested_type
            await _notify_user(
                db,
                user_id=change_request.requester_user_id,
                content=f"{user.nickname} 已确认建立关系，关系类型为“{pair_type_label(pair.type.value if pair.type else None)}”。",
                target_path=target_path,
            )
            await _record_pair_request_event(
                db,
                event_type="pair.join_approved",
                pair=pair,
                actor=user,
                request=change_request,
                extra_payload={
                    "requester_user_id": str(change_request.requester_user_id),
                    "requester_nickname": requester.nickname if requester else None,
                },
            )
        else:
            previous_type = pair.type.value if pair.type else None
            pair.type = change_request.requested_type
            await _notify_user(
                db,
                user_id=change_request.requester_user_id,
                content=(
                    f"{user.nickname} 已确认关系类型切换，"
                    f"现在按“{pair_type_label(pair.type.value if pair.type else None)}”处理。"
                ),
                target_path=target_path,
            )
            await _record_pair_request_event(
                db,
                event_type="pair.type_change_approved",
                pair=pair,
                actor=user,
                request=change_request,
                extra_payload={
                    "previous_type": previous_type,
                    "previous_type_label": pair_type_label(previous_type),
                },
            )

    else:
        change_request.status = PairChangeRequestStatus.REJECTED
        change_request.decided_at = _utcnow()

        if change_request.kind == PairChangeRequestKind.JOIN_REQUEST:
            pair.user_b_id = None
            pair.status = PairStatus.PENDING
            pair.type = None
            await _notify_user(
                db,
                user_id=change_request.requester_user_id,
                content=f"{user.nickname} 暂未确认这次加入请求，你可以稍后再发起。",
                target_path=target_path,
            )
            await _record_pair_request_event(
                db,
                event_type="pair.join_rejected",
                pair=pair,
                actor=user,
                request=change_request,
                extra_payload={
                    "requester_user_id": str(change_request.requester_user_id),
                    "requester_nickname": requester.nickname if requester else None,
                },
            )
        else:
            await _notify_user(
                db,
                user_id=change_request.requester_user_id,
                content=f"{user.nickname} 暂未确认这次关系类型切换，当前仍按原关系类型处理。",
                target_path=target_path,
            )
            await _record_pair_request_event(
                db,
                event_type="pair.type_change_rejected",
                pair=pair,
                actor=user,
                request=change_request,
            )

    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/cancel",
    response_model=PairChangeRequestBundleResponse,
)
async def cancel_pair_change_request(
    pair_id: str,
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起方主动取消一条待确认请求。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if str(change_request.requester_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有发起方可以取消这条请求")
    if (
        change_request.kind == PairChangeRequestKind.BREAK_REQUEST
        and change_request.phase == PairChangeRequestPhase.RETAINING
    ):
        raise HTTPException(status_code=409, detail="进入挽留阶段后不能直接撤回，请做最终决定")

    change_request.status = PairChangeRequestStatus.CANCELLED
    if change_request.kind == PairChangeRequestKind.BREAK_REQUEST:
        change_request.resolution_reason = (
            PairChangeRequestResolutionReason.REQUESTER_CANCELLED
        )
    change_request.decided_at = _utcnow()

    if change_request.kind == PairChangeRequestKind.JOIN_REQUEST:
        pair.user_b_id = None
        pair.status = PairStatus.PENDING
        pair.type = None
    elif change_request.kind == PairChangeRequestKind.BREAK_REQUEST:
        pair.status = PairStatus.ACTIVE
    approver = await db.get(User, change_request.approver_user_id)
    await _notify_user(
        db,
        user_id=change_request.approver_user_id,
        content=f"{user.nickname} 已撤回这次{_change_kind_label(change_request.kind)}请求。",
        target_path=_relationship_detail_path(pair.id),
    )
    await _record_pair_request_event(
        db,
        event_type="pair.request_cancelled",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={
            "approver_user_id": str(change_request.approver_user_id),
            "approver_nickname": approver.nickname if approver else None,
        },
    )

    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post("/{pair_id}/break-request", response_model=PairChangeRequestBundleResponse)
async def create_break_request(
    pair_id: str,
    req: PairBreakRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起断绝关系申请。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    await _sync_expired_break_requests_for_pair(db, pair)
    await _ensure_no_pending_request(db, pair.id)

    approver_user_id = pair.user_b_id if pair.user_a_id == user.id else pair.user_a_id
    if not approver_user_id:
        raise HTTPException(status_code=409, detail="这段关系还没有完成建立")

    phase = (
        PairChangeRequestPhase.AWAITING_RETENTION_CHOICE
        if req.allow_retention
        else PairChangeRequestPhase.AWAITING_TIMEOUT
    )
    change_request = PairChangeRequest(
        pair_id=pair.id,
        kind=PairChangeRequestKind.BREAK_REQUEST,
        status=PairChangeRequestStatus.PENDING,
        requester_user_id=user.id,
        approver_user_id=approver_user_id,
        allow_retention=req.allow_retention,
        phase=phase,
        expires_at=_utcnow() + BREAK_REQUEST_CHOICE_WINDOW,
    )
    db.add(change_request)
    await db.flush()

    approver = await db.get(User, approver_user_id)
    target_path = _relationship_detail_path(pair.id)
    if req.allow_retention:
        await _notify_user(
            db,
            user_id=approver_user_id,
            content=(
                f"{user.nickname} 发起了断绝关系申请。你可以在 24 小时内选择是否挽留。"
            ),
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=user.id,
            content=f"已发起断绝关系申请，等待 {approver.nickname if approver else '对方'} 选择是否挽留。",
            target_path=target_path,
        )
    else:
        await _notify_user(
            db,
            user_id=approver_user_id,
            content=f"{user.nickname} 发起了断绝关系申请。这段关系将在 24 小时后自动解除。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=user.id,
            content="已发起断绝关系申请，这段关系将在 24 小时后自动解除。",
            target_path=target_path,
        )

    await _record_pair_request_event(
        db,
        event_type="pair.break_requested",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={
            "approver_user_id": str(approver_user_id),
            "approver_nickname": approver.nickname if approver else None,
        },
    )
    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/retain",
    response_model=PairChangeRequestBundleResponse,
)
async def retain_break_request(
    pair_id: str,
    request_id: str,
    req: PairBreakRetentionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对方选择挽留，并提交首条说明。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="只有断绝关系请求支持挽留")
    if str(change_request.approver_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有对方可以发起挽留")
    if not change_request.allow_retention:
        raise HTTPException(status_code=409, detail="这次申请没有开放挽留")
    if change_request.phase != PairChangeRequestPhase.AWAITING_RETENTION_CHOICE:
        raise HTTPException(status_code=409, detail="当前阶段不能发起挽留")

    await _create_change_request_message(
        db,
        request_id=change_request.id,
        sender_user_id=user.id,
        message=req.message,
    )
    change_request.phase = PairChangeRequestPhase.RETAINING
    change_request.expires_at = _utcnow() + BREAK_REQUEST_RETENTION_WINDOW

    requester = await db.get(User, change_request.requester_user_id)
    target_path = _relationship_detail_path(pair.id)
    await _notify_user(
        db,
        user_id=change_request.requester_user_id,
        content=f"{user.nickname} 选择了挽留，并提交了第一条说明。请在 12 小时内决定是否接受。",
        target_path=target_path,
    )
    await _notify_user(
        db,
        user_id=user.id,
        content=f"你已向 {requester.nickname if requester else '对方'} 提交挽留说明，现在进入 12 小时挽留阶段。",
        target_path=target_path,
    )
    await _record_pair_request_event(
        db,
        event_type="pair.break_retention_started",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={
            "requester_nickname": requester.nickname if requester else None,
            "message_count": 1,
        },
    )
    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/decline-break",
    response_model=PairChangeRequestBundleResponse,
)
async def decline_break_request(
    pair_id: str,
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对方选择不挽留，直接断绝关系。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="只有断绝关系请求支持这个操作")
    if str(change_request.approver_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有对方可以决定是否挽留")
    if change_request.phase != PairChangeRequestPhase.AWAITING_RETENTION_CHOICE:
        raise HTTPException(status_code=409, detail="当前阶段不能直接断绝")

    change_request.status = PairChangeRequestStatus.APPROVED
    change_request.resolution_reason = (
        PairChangeRequestResolutionReason.PARTNER_DECLINED
    )
    change_request.decided_at = _utcnow()
    pair.status = PairStatus.ENDED

    requester = await db.get(User, change_request.requester_user_id)
    target_path = _relationship_detail_path(pair.id)
    await _notify_user(
        db,
        user_id=change_request.requester_user_id,
        content=f"{user.nickname} 选择不挽留，这段关系现已解除。",
        target_path=target_path,
    )
    await _notify_user(
        db,
        user_id=user.id,
        content="你已选择仍然断绝，这段关系现已解除。",
        target_path=target_path,
    )
    await _record_pair_request_event(
        db,
        event_type="pair.break_declined_by_partner",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={"requester_nickname": requester.nickname if requester else None},
    )
    await _record_pair_request_event(
        db,
        event_type="pair.break_completed",
        pair=pair,
        actor=user,
        request=change_request,
        extra_payload={"requester_nickname": requester.nickname if requester else None},
    )
    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/messages",
    response_model=PairChangeRequestBundleResponse,
)
async def append_break_request_message(
    pair_id: str,
    request_id: str,
    req: PairBreakMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在挽留阶段继续追加留言。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="只有断绝关系请求支持留言")
    if change_request.phase != PairChangeRequestPhase.RETAINING:
        raise HTTPException(status_code=409, detail="当前不在挽留阶段，不能追加留言")
    if str(change_request.approver_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有挽留方可以继续追加留言")

    await _create_change_request_message(
        db,
        request_id=change_request.id,
        sender_user_id=user.id,
        message=req.message,
    )
    requester = await db.get(User, change_request.requester_user_id)
    target_path = _relationship_detail_path(pair.id)
    await _notify_user(
        db,
        user_id=change_request.requester_user_id,
        content=f"{user.nickname} 追加了一条新的挽留说明。",
        target_path=target_path,
    )
    await _notify_user(
        db,
        user_id=user.id,
        content=f"你又补充了一条留给 {requester.nickname if requester else '对方'} 的说明。",
        target_path=target_path,
    )
    await _record_pair_request_event(
        db,
        event_type="pair.break_retention_message_added",
        pair=pair,
        actor=user,
        request=change_request,
    )
    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.post(
    "/{pair_id}/change-requests/{request_id}/retention-decision",
    response_model=PairChangeRequestBundleResponse,
)
async def decide_break_request_retention(
    pair_id: str,
    request_id: str,
    req: PairBreakRetentionDecisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起方决定是否接受挽留。"""
    pair, change_request = await _get_change_request_for_decision(
        db, pair_id=pair_id, request_id=request_id, user=user
    )
    if change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="只有断绝关系请求支持这个操作")
    if str(change_request.requester_user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有发起方可以决定是否接受挽留")
    if change_request.phase != PairChangeRequestPhase.RETAINING:
        raise HTTPException(status_code=409, detail="当前不在挽留决定阶段")

    approver = await db.get(User, change_request.approver_user_id)
    target_path = _relationship_detail_path(pair.id)
    if req.decision == "accept":
        change_request.status = PairChangeRequestStatus.REJECTED
        change_request.resolution_reason = (
            PairChangeRequestResolutionReason.RETENTION_ACCEPTED
        )
        change_request.decided_at = _utcnow()
        pair.status = PairStatus.ACTIVE
        await _notify_user(
            db,
            user_id=change_request.approver_user_id,
            content=f"{user.nickname} 接受了你的挽留，这段关系已恢复正常。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=user.id,
            content="你已接受这次挽留，关系恢复正常，这条记录会留作后台证据。",
            target_path=target_path,
        )
        await _record_pair_request_event(
            db,
            event_type="pair.break_cancelled_by_retention",
            pair=pair,
            actor=user,
            request=change_request,
            extra_payload={"approver_nickname": approver.nickname if approver else None},
        )
    else:
        change_request.status = PairChangeRequestStatus.APPROVED
        change_request.resolution_reason = (
            PairChangeRequestResolutionReason.RETENTION_REJECTED
        )
        change_request.decided_at = _utcnow()
        pair.status = PairStatus.ENDED
        await _notify_user(
            db,
            user_id=change_request.approver_user_id,
            content=f"{user.nickname} 最终仍然选择断绝关系，这段关系现已解除。",
            target_path=target_path,
        )
        await _notify_user(
            db,
            user_id=user.id,
            content="你已选择仍然断绝，这段关系现已解除。",
            target_path=target_path,
        )
        await _record_pair_request_event(
            db,
            event_type="pair.break_completed",
            pair=pair,
            actor=user,
            request=change_request,
            extra_payload={"approver_nickname": approver.nickname if approver else None},
        )

    return await _build_pair_bundle_response(
        db, pair=pair, me=user, request=change_request
    )


@router.get("/summary", response_model=PairSummaryResponse)
async def get_pair_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取当前用户配对摘要，便于前端统一同步绑定状态。"""
    await _sync_expired_break_requests_for_user(db, user)
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    pairs = result.scalars().all()

    active_pairs = [pair for pair in pairs if pair.status == PairStatus.ACTIVE]
    pending_pairs = [pair for pair in pairs if pair.status == PairStatus.PENDING]

    active_pair = active_pairs[0] if active_pairs else None
    pair_response = None
    if active_pair:
        partner = await _resolve_partner_for_pair(db, active_pair, user)
        pair_response = await _build_pair_response(db, active_pair, user, partner)

    return PairSummaryResponse(
        is_paired=bool(active_pairs),
        active_pair=pair_response,
        active_count=len(active_pairs),
        pending_count=len(pending_pairs),
    )


# ── 兼容旧解绑接口（统一转入新的断绝关系流程）──


@router.post("/request-unbind", response_model=dict)
async def request_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧接口：默认按“给对方挽留机会”的新流程发起断绝关系。"""
    bundle = await create_break_request(
        pair_id,
        PairBreakRequest(allow_retention=True),
        user,
        db,
    )
    return {
        "message": "已按新流程发起断绝关系申请，并默认给对方挽留机会。",
        "request": bundle.request.model_dump(mode="json"),
    }


@router.post("/confirm-unbind", response_model=dict)
async def confirm_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧接口：在新流程中执行“仍然断绝”动作。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=False)
    await _sync_expired_break_requests_for_pair(db, pair)
    change_request = await _get_pending_change_request(db, pair.id)
    if not change_request or change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="没有待处理的断绝关系申请")

    if (
        str(change_request.approver_user_id) == str(user.id)
        and change_request.phase == PairChangeRequestPhase.AWAITING_RETENTION_CHOICE
    ):
        bundle = await decline_break_request(pair_id, str(change_request.id), user, db)
        return {
            "message": "已按新流程确认仍然断绝，关系现已解除。",
            "request": bundle.request.model_dump(mode="json"),
        }

    if (
        str(change_request.requester_user_id) == str(user.id)
        and change_request.phase == PairChangeRequestPhase.RETAINING
    ):
        bundle = await decide_break_request_retention(
            pair_id,
            str(change_request.id),
            PairBreakRetentionDecisionRequest(decision="reject"),
            user,
            db,
        )
        return {
            "message": "已在挽留阶段确认仍然断绝，关系现已解除。",
            "request": bundle.request.model_dump(mode="json"),
        }

    raise HTTPException(status_code=400, detail="当前阶段不能通过旧解绑接口确认解除")


@router.post("/cancel-unbind", response_model=dict)
async def cancel_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧接口：撤回首阶段的断绝关系申请。"""
    pair = await validate_pair_access(pair_id, user, db, require_active=False)
    await _sync_expired_break_requests_for_pair(db, pair)
    change_request = await _get_pending_change_request(db, pair.id)
    if not change_request or change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        raise HTTPException(status_code=400, detail="没有待处理的断绝关系申请")
    bundle = await cancel_pair_change_request(pair_id, str(change_request.id), user, db)
    return {
        "message": "已撤回断绝关系申请。",
        "request": bundle.request.model_dump(mode="json"),
    }


@router.get("/unbind-status", response_model=dict)
async def get_unbind_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧接口：返回新断绝关系流程的摘要状态。"""
    try:
        pair = await validate_pair_access(pair_id, user, db, require_active=False)
    except HTTPException:
        return {"has_request": False}

    await _sync_expired_break_requests_for_pair(db, pair)
    change_request = await _get_pending_change_request(db, pair.id)
    if not change_request or change_request.kind != PairChangeRequestKind.BREAK_REQUEST:
        return {"has_request": False}

    remaining_seconds = 0
    if change_request.expires_at:
        remaining_seconds = max(
            0,
            int((change_request.expires_at - _utcnow()).total_seconds()),
        )
    return {
        "has_request": True,
        "requested_by_me": str(change_request.requester_user_id) == str(user.id),
        "waiting_for_me": _is_waiting_for_me(change_request, user),
        "allow_retention": bool(change_request.allow_retention),
        "phase": change_request.phase.value if change_request.phase else None,
        "remaining_seconds": remaining_seconds,
        "can_force_unbind": False,
    }


@router.get("/{pair_id}/task-settings", response_model=PairTaskPlannerSettingsResponse)
async def get_pair_task_settings(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    return _serialize_task_settings_response(pair=pair, user=user)


@router.patch("/{pair_id}/task-settings", response_model=PairTaskPlannerSettingsResponse)
async def update_pair_task_settings(
    pair_id: str,
    req: PairTaskPlannerSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    pair.task_planner_settings = merge_pair_task_planner_overrides(
        pair.task_planner_settings,
        req.model_dump(exclude_unset=True),
    )
    today = current_local_date()
    await reset_unstarted_system_tasks(
        db,
        pair_id=pair.id,
        target_dates=[today, today + timedelta(days=1)],
    )
    await db.flush()
    return _serialize_task_settings_response(pair=pair, user=user)


@router.post("/{pair_id}/partner-nickname", response_model=PairResponse)
async def update_partner_nickname(
    pair_id: str,
    req: UpdatePartnerNicknameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新给伴侣设置的备注名（自定义昵称）"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    custom_nickname = req.custom_nickname.strip() or None

    if str(pair.user_a_id) == str(user.id):
        pair.custom_partner_nickname_a = custom_nickname
    else:
        pair.custom_partner_nickname_b = custom_nickname

    await db.flush()

    partner = await _resolve_partner_for_pair(db, pair, user)
    return await _build_pair_response(db, pair, user, partner)

"""Narrative alignment insight routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.ai.narrative_alignment import generate_narrative_alignment
from app.core.database import get_db
from app.core.time import current_local_date
from app.models import RelationshipEvent, RelationshipProfileSnapshot, User
from app.schemas import NarrativeAlignmentResponse
from app.services.behavior_judgement import (
    apply_judgement_to_payload,
    judge_behavior_against_baseline,
)
from app.services.interaction_events import (
    build_interaction_payload,
    record_user_interaction_event,
)
from app.services.privacy_audit import privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
    refresh_profile_snapshot,
)
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.test_accounts import is_relaxed_test_account

from .shared import (
    get_latest_completed_report,
    get_latest_dual_checkins,
    get_latest_pair_plan,
    serialize_checkin,
)

router = APIRouter(tags=["关系智能"])
ALIGNMENT_GENERATE_WINDOW_SECONDS = 60
ALIGNMENT_GENERATE_MAX_ATTEMPTS = 2


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _history_rank(value: str | None) -> int:
    return {"insufficient": 0, "limited": 1, "sufficient": 2}.get(str(value or ""), 0)


def _combine_history_sufficiency(values: list[str | None]) -> str:
    if not values:
        return "insufficient"
    ranked = min(values, key=_history_rank)
    return str(ranked or "insufficient")


def _combine_reaction_shift(
    user_a_label: str,
    judgement_a: dict,
    user_b_label: str,
    judgement_b: dict,
) -> str | None:
    shifts = []
    shift_a = str(judgement_a.get("reaction_shift") or "").strip()
    shift_b = str(judgement_b.get("reaction_shift") or "").strip()
    if shift_a and shift_a not in {"stable", "unknown"}:
        shifts.append(f"{user_a_label}：{shift_a}")
    if shift_b and shift_b not in {"stable", "unknown"}:
        shifts.append(f"{user_b_label}：{shift_b}")
    if not shifts:
        if shift_a == "unknown" or shift_b == "unknown":
            return "unknown"
        return "stable"
    return "；".join(shifts)


def _alignment_cache_key(
    pair_id: uuid.UUID,
    checkin_a_id: uuid.UUID,
    checkin_b_id: uuid.UUID,
) -> str:
    return f"alignment:{pair_id}:{checkin_a_id}:{checkin_b_id}"


def _coerce_datetime(value: object, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return fallback
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    return fallback


def _current_risk_level(snapshot: RelationshipProfileSnapshot | None) -> str:
    return str((getattr(snapshot, "risk_summary", None) or {}).get("current_level") or "none")


async def _get_latest_pair_snapshot_read_only(
    db: AsyncSession,
    pair_id: uuid.UUID,
) -> RelationshipProfileSnapshot | None:
    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id.is_(None),
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_cached_alignment_event(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    checkin_a_id: uuid.UUID,
    checkin_b_id: uuid.UUID,
) -> RelationshipEvent | None:
    cache_key = _alignment_cache_key(pair_id, checkin_a_id, checkin_b_id)
    result = await db.execute(
        select(RelationshipEvent)
        .where(RelationshipEvent.idempotency_key == cache_key)
        .limit(1)
    )
    cached = result.scalar_one_or_none()
    if cached:
        return cached

    legacy_result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.event_type == "alignment.generated",
        )
        .order_by(desc(RelationshipEvent.occurred_at))
        .limit(10)
    )
    for event in legacy_result.scalars().all():
        payload = event.payload or {}
        if str(payload.get("checkin_a_id") or "") == str(checkin_a_id) and str(
            payload.get("checkin_b_id") or ""
        ) == str(checkin_b_id):
            return event
    return None


def _build_alignment_response(
    *,
    event_id: uuid.UUID | None,
    pair_id: uuid.UUID,
    checkin_date,
    user_a_label: str,
    user_b_label: str,
    payload: dict,
    current_risk_level: str,
    active_plan_type: str | None,
    generated_at: datetime,
) -> NarrativeAlignmentResponse:
    return NarrativeAlignmentResponse(
        event_id=event_id,
        pair_id=pair_id,
        checkin_date=checkin_date,
        user_a_label=user_a_label,
        user_b_label=user_b_label,
        alignment_score=int(payload.get("alignment_score") or 0),
        shared_story=payload.get("shared_story") or "双方的故事正在等待对齐。",
        view_a_summary=payload.get("view_a_summary") or "A方的关注点暂未识别。",
        view_b_summary=payload.get("view_b_summary") or "B方的关注点暂未识别。",
        misread_risk=payload.get("misread_risk") or "当前最容易错位的点暂未识别。",
        divergence_points=list(payload.get("divergence_points") or []),
        bridge_actions=list(payload.get("bridge_actions") or []),
        suggested_opening=payload.get("suggested_opening"),
        coach_note=payload.get("coach_note"),
        reaction_shift=payload.get("reaction_shift"),
        deviation_reasons=list(payload.get("deviation_reasons") or []),
        history_sufficiency=payload.get("history_sufficiency"),
        current_risk_level=payload.get("current_risk_level") or current_risk_level,
        active_plan_type=payload.get("active_plan_type") or active_plan_type,
        source=payload.get("source") or "ai",
        is_fallback=bool(payload.get("is_fallback")),
        generated_at=generated_at,
    )


def _build_context(
    *,
    pair,
    snapshot: RelationshipProfileSnapshot | None,
    active_plan,
    latest_report,
) -> dict:
    report_content = (latest_report.content or {}) if latest_report else {}
    return {
        "pair_type": pair.type.value,
        "is_long_distance": bool(pair.is_long_distance),
        "current_risk_level": _current_risk_level(snapshot),
        "risk_trend": (getattr(snapshot, "risk_summary", None) or {}).get(
            "trend", "unknown"
        ),
        "suggested_focus": (getattr(snapshot, "suggested_focus", None) or {}).get(
            "items", []
        ),
        "attachment_summary": getattr(snapshot, "attachment_summary", None) or {},
        "latest_report": {
            "type": latest_report.type.value if latest_report else None,
            "report_date": (
                latest_report.report_date.isoformat() if latest_report else None
            ),
            "insight": (
                report_content.get("insight")
                or report_content.get("executive_summary")
                or report_content.get("trend_description")
                or report_content.get("self_insight")
            ),
            "suggestion": (
                report_content.get("suggestion")
                or report_content.get("self_care_tip")
                or report_content.get("professional_note")
                or report_content.get("trend_description")
            ),
        },
        "active_plan": {
            "plan_type": active_plan.plan_type if active_plan else None,
            "risk_level": active_plan.risk_level if active_plan else None,
            "primary_goal": (
                (active_plan.goal_json or {}).get("primary_goal")
                if active_plan
                else None
            ),
            "focus": (
                (active_plan.goal_json or {}).get("focus", []) if active_plan else []
            ),
        },
    }


async def _resolve_alignment_read_context(
    db: AsyncSession,
    *,
    pair,
) -> tuple[RelationshipProfileSnapshot | None, object | None, User | None, User | None]:
    pair_uuid = pair.id
    snapshot = await _get_latest_pair_snapshot_read_only(db, pair_uuid)
    active_plan = await get_latest_pair_plan(db, pair_uuid)
    user_a = await db.get(User, pair.user_a_id)
    user_b = await db.get(User, pair.user_b_id)
    return snapshot, active_plan, user_a, user_b


async def _build_relaxed_insufficient_alignment_response(
    db: AsyncSession,
    *,
    pair,
) -> NarrativeAlignmentResponse:
    user_a = await db.get(User, pair.user_a_id)
    user_b = await db.get(User, pair.user_b_id)
    generated_at = _utcnow()
    payload = {
        "alignment_score": 50,
        "shared_story": "测试账号可在双方记录不足时先查看双视角功能流。",
        "view_a_summary": "A方记录样本还不足，当前结果仅用于测试入口与展示。",
        "view_b_summary": "B方记录样本还不足，当前结果仅用于测试入口与展示。",
        "misread_risk": "样本不足时不做真实关系判断。",
        "divergence_points": ["测试占位结果不会替代真实双方记录分析"],
        "bridge_actions": ["继续补充双方记录后再生成正式双视角"],
        "suggested_opening": "我们先各写一条最近真实感受，再看正式双视角。",
        "coach_note": "这是测试号的放开权限结果，用来验证功能流。",
        "reaction_shift": "unknown",
        "deviation_reasons": [],
        "history_sufficiency": "insufficient",
        "source": "fallback",
        "is_fallback": True,
        "generated_at": generated_at,
    }
    return _build_alignment_response(
        event_id=None,
        pair_id=pair.id,
        checkin_date=current_local_date(),
        user_a_label=user_a.nickname if user_a else "A方",
        user_b_label=user_b.nickname if user_b else "B方",
        payload=payload,
        current_risk_level="none",
        active_plan_type=None,
        generated_at=generated_at,
    )


@router.get(
    "/alignment/latest",
    response_model=NarrativeAlignmentResponse | None,
)
async def get_latest_narrative_alignment(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    checkin_a, checkin_b = await get_latest_dual_checkins(db, pair)
    if not checkin_a or not checkin_b:
        return None

    snapshot, active_plan, user_a, user_b = await _resolve_alignment_read_context(
        db, pair=pair
    )
    cached_event = await _get_cached_alignment_event(
        db,
        pair_id=pair.id,
        checkin_a_id=checkin_a.id,
        checkin_b_id=checkin_b.id,
    )
    if not cached_event:
        return None

    payload = cached_event.payload or {}
    return _build_alignment_response(
        event_id=cached_event.id,
        pair_id=pair.id,
        checkin_date=checkin_a.checkin_date,
        user_a_label=user_a.nickname if user_a else "A方",
        user_b_label=user_b.nickname if user_b else "B方",
        payload=payload,
        current_risk_level=_current_risk_level(snapshot),
        active_plan_type=active_plan.plan_type if active_plan else None,
        generated_at=_coerce_datetime(payload.get("generated_at"), cached_event.occurred_at),
    )


@router.post(
    "/alignment/generate",
    response_model=NarrativeAlignmentResponse,
)
async def generate_latest_narrative_alignment(
    pair_id: str,
    force: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    checkin_a, checkin_b = await get_latest_dual_checkins(db, pair)
    if not checkin_a or not checkin_b:
        if is_relaxed_test_account(user):
            return await _build_relaxed_insufficient_alignment_response(db, pair=pair)
        raise HTTPException(
            status_code=404,
            detail="还没有足够的双方记录，暂时无法生成双视角叙事对齐。",
        )

    cached_event = await _get_cached_alignment_event(
        db,
        pair_id=pair.id,
        checkin_a_id=checkin_a.id,
        checkin_b_id=checkin_b.id,
    )
    if cached_event and not force:
        snapshot, active_plan, user_a, user_b = await _resolve_alignment_read_context(
            db, pair=pair
        )
        payload = cached_event.payload or {}
        return _build_alignment_response(
            event_id=cached_event.id,
            pair_id=pair.id,
            checkin_date=checkin_a.checkin_date,
            user_a_label=user_a.nickname if user_a else "A方",
            user_b_label=user_b.nickname if user_b else "B方",
            payload=payload,
            current_risk_level=_current_risk_level(snapshot),
            active_plan_type=active_plan.plan_type if active_plan else None,
            generated_at=_coerce_datetime(
                payload.get("generated_at"), cached_event.occurred_at
            ),
        )

    await consume_request_cooldown(
        bucket="alignment-generate",
        scope_key=f"{user.id}:{pair.id}",
        window_seconds=ALIGNMENT_GENERATE_WINDOW_SECONDS,
        max_attempts=ALIGNMENT_GENERATE_MAX_ATTEMPTS,
        limit_message="双视角整理得有点频繁了",
        bypass=is_relaxed_test_account(user),
    )

    pair_snapshot = await refresh_profile_snapshot(db, pair_id=pair.id, window_days=7)
    active_plan = await get_latest_pair_plan(db, pair.id)
    latest_report = await get_latest_completed_report(db, pair.id)
    user_a = await db.get(User, pair.user_a_id)
    user_b = await db.get(User, pair.user_b_id)
    user_a_baseline = await refresh_profile_snapshot(
        db, user_id=pair.user_a_id, window_days=30
    )
    user_b_baseline = await refresh_profile_snapshot(
        db, user_id=pair.user_b_id, window_days=30
    )
    await db.commit()

    context = _build_context(
        pair=pair,
        snapshot=pair_snapshot,
        active_plan=active_plan,
        latest_report=latest_report,
    )

    user_a_label = user_a.nickname if user_a else "A方"
    user_b_label = user_b.nickname if user_b else "B方"
    with privacy_audit_scope(
        db=db,
        user_id=user.id,
        pair_id=pair.id,
        scope="pair",
        run_type="narrative_alignment",
        privacy_mode=resolve_privacy_mode(getattr(user, "product_prefs", None)),
    ):
        alignment = await generate_narrative_alignment(
            context=context,
            checkin_a=serialize_checkin(checkin_a, user_a_label),
            checkin_b=serialize_checkin(checkin_b, user_b_label),
        )

    judgement_a = judge_behavior_against_baseline(
        checkin_a.content,
        baseline_summary=getattr(user_a_baseline, "behavior_summary", None),
        risk_level=context["current_risk_level"],
        sentiment_hint=checkin_a.sentiment_score,
    )
    judgement_b = judge_behavior_against_baseline(
        checkin_b.content,
        baseline_summary=getattr(user_b_baseline, "behavior_summary", None),
        risk_level=context["current_risk_level"],
        sentiment_hint=checkin_b.sentiment_score,
    )
    deviation_reasons = [
        f"{user_a_label}：{reason}"
        for reason in (judgement_a.get("deviation_reasons") or [])
    ] + [
        f"{user_b_label}：{reason}"
        for reason in (judgement_b.get("deviation_reasons") or [])
    ]
    history_sufficiency = _combine_history_sufficiency(
        [
            judgement_a.get("history_sufficiency"),
            judgement_b.get("history_sufficiency"),
        ]
    )
    reaction_shift = _combine_reaction_shift(
        user_a_label,
        judgement_a,
        user_b_label,
        judgement_b,
    )
    generated_at = _utcnow()
    response = NarrativeAlignmentResponse(
        event_id=cached_event.id if cached_event else None,
        pair_id=pair.id,
        checkin_date=checkin_a.checkin_date,
        user_a_label=user_a_label,
        user_b_label=user_b_label,
        alignment_score=int(alignment.get("alignment_score") or 0),
        shared_story=alignment.get("shared_story") or "双方的故事正在等待对齐。",
        view_a_summary=alignment.get("view_a_summary") or "A方的关注点暂未识别。",
        view_b_summary=alignment.get("view_b_summary") or "B方的关注点暂未识别。",
        misread_risk=alignment.get("misread_risk") or "当前最容易错位的点暂未识别。",
        divergence_points=alignment.get("divergence_points") or [],
        bridge_actions=alignment.get("bridge_actions") or [],
        suggested_opening=alignment.get("suggested_opening"),
        coach_note=alignment.get("coach_note"),
        reaction_shift=reaction_shift,
        deviation_reasons=deviation_reasons[:4],
        history_sufficiency=history_sufficiency,
        current_risk_level=context["current_risk_level"],
        active_plan_type=active_plan.plan_type if active_plan else None,
        algorithm_version=alignment.get("algorithm_version"),
        confidence=alignment.get("confidence"),
        decision_trace=alignment.get("decision_trace") or {},
        focus_labels=alignment.get("focus_labels") or [],
        risk_score=alignment.get("risk_score"),
        baseline_delta=alignment.get("baseline_delta"),
        fallback_reason=alignment.get("fallback_reason"),
        shadow_result=alignment.get("shadow_result"),
        feedback_status=alignment.get("feedback_status"),
        source=alignment.get("source") or "ai",
        is_fallback=bool(alignment.get("is_fallback")),
        generated_at=generated_at,
    )
    alignment_payload = apply_judgement_to_payload(
        {
            **response.model_dump(mode="json"),
            "checkin_a_id": str(checkin_a.id),
            "checkin_b_id": str(checkin_b.id),
            "user_a_baseline_match": judgement_a.get("baseline_match"),
            "user_b_baseline_match": judgement_b.get("baseline_match"),
        },
        text=response.shared_story,
        risk_level=context["current_risk_level"],
    )
    cache_key = _alignment_cache_key(pair.id, checkin_a.id, checkin_b.id)

    if cached_event:
        cached_event.user_id = user.id
        cached_event.entity_type = "pair"
        cached_event.entity_id = str(pair.id)
        cached_event.source = "system"
        cached_event.payload = alignment_payload
        cached_event.idempotency_key = cache_key
        cached_event.occurred_at = generated_at
        await db.flush()
    else:
        cached_event = await record_relationship_event(
            db,
            event_type="alignment.generated",
            pair_id=pair.id,
            user_id=user.id,
            entity_type="pair",
            entity_id=pair.id,
            payload=alignment_payload,
            idempotency_key=cache_key,
            occurred_at=generated_at,
        )

    response.event_id = cached_event.id if cached_event else response.event_id

    await record_user_interaction_event(
        db,
        event_type="insights.alignment.generated",
        user_id=user.id,
        pair_id=pair.id,
        source="insights",
        page="alignment",
        path="/alignment",
        http_method="POST",
        http_status=200,
        target_type="pair",
        target_id=pair.id,
        payload=build_interaction_payload(
            {
                "alignment_score": response.alignment_score,
                "shared_story": response.shared_story,
                "misread_risk": response.misread_risk,
                "reaction_shift": response.reaction_shift,
                "deviation_reasons": response.deviation_reasons,
                "history_sufficiency": response.history_sufficiency,
                "source": response.source,
                "is_fallback": response.is_fallback,
            },
            text=response.shared_story,
            risk_level=context["current_risk_level"],
        ),
    )
    await refresh_profile_and_plan(db, pair_id=pair.id)
    await db.commit()

    return response

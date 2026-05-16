"""Narrative alignment insight routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.ai.narrative_alignment import generate_narrative_alignment
from app.core.database import get_db
from app.models import User
from app.schemas import NarrativeAlignmentResponse
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)
from app.services.privacy_audit import privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode

from .shared import (
    get_latest_completed_report,
    get_latest_dual_checkins,
    get_latest_pair_plan,
    get_latest_pair_snapshot,
    serialize_checkin,
)

router = APIRouter(tags=["关系智能"])


@router.get(
    "/alignment/latest",
    response_model=NarrativeAlignmentResponse,
)
async def get_latest_narrative_alignment(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    checkin_a, checkin_b = await get_latest_dual_checkins(db, pair)
    if not checkin_a or not checkin_b:
        raise HTTPException(
            status_code=404,
            detail="还没有足够的双方记录，暂时无法生成双视角叙事对齐。",
        )

    snapshot = await get_latest_pair_snapshot(db, pair_id)
    active_plan = await get_latest_pair_plan(db, pair_id)
    latest_report = await get_latest_completed_report(db, pair_id)
    user_a = await db.get(User, pair.user_a_id)
    user_b = await db.get(User, pair.user_b_id)

    report_content = (latest_report.content or {}) if latest_report else {}
    context = {
        "pair_type": pair.type.value,
        "is_long_distance": bool(pair.is_long_distance),
        "current_risk_level": (snapshot.risk_summary or {}).get(
            "current_level", "none"
        ),
        "risk_trend": (snapshot.risk_summary or {}).get("trend", "unknown"),
        "suggested_focus": (snapshot.suggested_focus or {}).get("items", []),
        "attachment_summary": snapshot.attachment_summary or {},
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
            checkin_a=serialize_checkin(checkin_a, user_a.nickname if user_a else "A方"),
            checkin_b=serialize_checkin(checkin_b, user_b.nickname if user_b else "B方"),
        )

    await record_relationship_event(
        db,
        event_type="alignment.generated",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="pair",
        entity_id=pair.id,
        payload={
            "checkin_date": checkin_a.checkin_date.isoformat(),
            "alignment_score": alignment.get("alignment_score"),
            "current_risk_level": context["current_risk_level"],
            "shared_story": alignment.get("shared_story"),
            "misread_risk": alignment.get("misread_risk"),
            "suggested_opening": alignment.get("suggested_opening"),
            "bridge_actions": alignment.get("bridge_actions") or [],
        },
    )
    await refresh_profile_and_plan(db, pair_id=pair.id)
    await db.commit()

    return NarrativeAlignmentResponse(
        pair_id=pair.id,
        checkin_date=checkin_a.checkin_date,
        user_a_label=user_a.nickname if user_a else "A方",
        user_b_label=user_b.nickname if user_b else "B方",
        alignment_score=int(alignment.get("alignment_score") or 0),
        shared_story=alignment.get("shared_story") or "双方的故事正在等待对齐。",
        view_a_summary=alignment.get("view_a_summary") or "A方的关注点暂未识别。",
        view_b_summary=alignment.get("view_b_summary") or "B方的关注点暂未识别。",
        misread_risk=alignment.get("misread_risk") or "当前最容易错位的点暂未识别。",
        divergence_points=alignment.get("divergence_points") or [],
        bridge_actions=alignment.get("bridge_actions") or [],
        suggested_opening=alignment.get("suggested_opening"),
        coach_note=alignment.get("coach_note"),
        current_risk_level=context["current_risk_level"],
        active_plan_type=active_plan.plan_type if active_plan else None,
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

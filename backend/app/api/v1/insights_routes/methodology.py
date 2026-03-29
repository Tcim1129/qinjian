"""Methodology insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import MethodologyResponse
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_theory import (
    build_methodology_summary,
    build_repair_protocol_theory_basis,
    build_task_strategy_theory_basis,
)
from app.services.playbook_runtime import sync_active_playbook_runtime
from app.services.relationship_intelligence import record_relationship_event
from app.services.task_adaptation import build_task_adaptation_strategy

from .shared import dedupe_theory_cards, repair_protocol_type_for_level, resolve_scope

router = APIRouter(tags=["关系智能"])


@router.get(
    "/methodology",
    response_model=MethodologyResponse,
)
async def get_methodology(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    scorecard = await build_intervention_scorecard(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )
    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewed=False,
    )

    plan_type = (scorecard or {}).get("plan_type")
    risk_level = str(
        (scorecard or {}).get("risk_now")
        or (scorecard or {}).get("risk_level")
        or "none"
    )
    strategy = build_task_adaptation_strategy(scorecard)
    theory_cards: list[dict] = []

    if playbook:
        theory_cards.extend(playbook.get("theory_basis") or [])

    theory_cards.extend(
        build_task_strategy_theory_basis(
            plan_type=plan_type,
            intensity=strategy.get("intensity", "steady"),
            copy_mode=strategy.get("copy_mode"),
        )
    )

    if pair_scope_id:
        theory_cards.extend(
            build_repair_protocol_theory_basis(
                protocol_type=repair_protocol_type_for_level(risk_level),
                crisis_level=risk_level,
                active_plan_type=plan_type,
            )
        )

    payload = build_methodology_summary(
        plan_type=plan_type,
        is_pair=bool(pair_scope_id),
    )
    payload["theory_basis"] = dedupe_theory_cards(theory_cards)

    await record_relationship_event(
        db,
        event_type="methodology.viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="methodology",
        entity_id=f"{pair_scope_id or user_scope_id}",
        payload={
            "plan_type": plan_type,
            "is_pair": bool(pair_scope_id),
            "theory_count": len(payload["theory_basis"]),
        },
    )
    await db.commit()
    return MethodologyResponse(**payload)

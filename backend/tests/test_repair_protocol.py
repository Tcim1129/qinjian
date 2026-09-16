from datetime import date
from uuid import uuid4

from app.models import InterventionPlan, Pair, PairType, RelationshipProfileSnapshot
from app.services.repair_protocol import build_repair_protocol, build_solo_repair_protocol


def test_repair_protocol_includes_focus_tags_and_safety_handoff():
    pair = Pair(
        user_a_id=uuid4(),
        type=PairType.COUPLE,
        invite_code="A3H7K8M9Q2",
        is_long_distance=True,
    )
    active_plan = InterventionPlan(
        plan_type="low_connection_recovery",
        start_date=date(2026, 3, 21),
        goal_json={"primary_goal": "恢复稳定连接"},
    )
    snapshot = RelationshipProfileSnapshot(
        window_days=7,
        snapshot_date=date(2026, 3, 21),
        metrics_json={"interaction_overlap_rate": 0.42, "crisis_event_count": 2},
        suggested_focus={"items": ["repair_checkin", "response_window"]},
    )

    protocol = build_repair_protocol(
        pair=pair,
        crisis_level="severe",
        active_plan=active_plan,
        snapshot=snapshot,
    )

    assert protocol["protocol_type"] == "de_escalation_protocol"
    assert protocol["active_plan_type"] == "low_connection_recovery"
    assert protocol["focus_tags"][:2] == ["long_distance", "low_connection_recovery"]
    assert "repair_checkin" in protocol["focus_tags"]
    assert protocol["safety_handoff"] is not None
    assert protocol["theory_basis"]
    assert len(protocol["evidence_summary"]) >= 3


def test_solo_repair_protocol_focuses_on_self_regulation_and_support_boundaries():
    active_plan = InterventionPlan(
        plan_type="self_regulation_plan",
        start_date=date(2026, 4, 22),
        goal_json={"primary_goal": "先把自己稳住，再决定要不要推进沟通"},
    )
    snapshot = RelationshipProfileSnapshot(
        window_days=7,
        snapshot_date=date(2026, 4, 22),
        metrics_json={"mood_avg": 4.2, "task_completion_rate": 0.5},
        risk_summary={"trend": "rising"},
        suggested_focus={"items": ["self_regulation_plan", "clarify"]},
    )

    protocol = build_solo_repair_protocol(
        crisis_level="moderate",
        active_plan=active_plan,
        snapshot=snapshot,
    )

    assert protocol["protocol_type"] == "structured_repair"
    assert protocol["active_plan_type"] == "self_regulation_plan"
    assert protocol["focus_tags"][:2] == ["self_regulation_plan", "clarify"]
    assert protocol["steps"][0]["title"] == "先做身体降压"
    assert protocol["safety_handoff"] is not None
    assert len(protocol["evidence_summary"]) >= 3

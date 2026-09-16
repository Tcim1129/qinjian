from app.models import Pair
from app.services.intervention_theory import build_methodology_summary
from app.services.repair_protocol import build_repair_protocol


def test_repair_protocol_includes_chinese_display_labels():
    protocol = build_repair_protocol(
        pair=Pair(is_long_distance=False),
        crisis_level="moderate",
    )

    assert protocol["level"] == "moderate"
    assert protocol["level_label"] == "中度"
    assert protocol["protocol_type_label"] == "结构化修复方案"
    assert protocol["model_family"] == "rule_engine_with_safety_first"
    assert protocol["model_family_label"] == "安全优先的规则引擎"
    assert "moderate" not in " ".join(protocol["evidence_summary"])


def test_methodology_summary_keeps_machine_fields_and_adds_chinese_display_fields():
    summary = build_methodology_summary(
        plan_type="conflict_repair_plan",
        is_pair=True,
    )

    assert summary["system_name"] == "relationship_intervention_system_v1"
    assert summary["system_name_label"] == "关系行为干预系统第一版"
    assert summary["model_family"] == "rule_engine_with_feedback_loop"
    assert summary["model_family_label"] == "规则引擎与反馈闭环"

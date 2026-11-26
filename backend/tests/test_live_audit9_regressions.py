from types import SimpleNamespace

from app.ai import multi_agent
from app.services.display_labels import translate_inline_codes
from app.services.safety_summary import _build_evidence_summary, _build_why_now


def test_audit9_safety_summary_translates_stable_trend_to_chinese():
    snapshot = SimpleNamespace(
        metrics_json={"mood_avg": 7.5},
        risk_summary={"trend": "stable"},
    )
    evidence = _build_evidence_summary(
        scope_is_pair=False,
        risk_level="none",
        snapshot=snapshot,
        active_plan=None,
        active_alert=None,
        latest_report=None,
    )
    joined = " ".join(evidence)
    assert "stable" not in joined.lower()
    assert "保持平稳" in joined
    reason = _build_why_now(scope_is_pair=False, risk_level="none", active_plan=None, active_alert=None, snapshot=snapshot)
    assert "stable" not in reason.lower()
    assert "保持平稳" in reason
    assert translate_inline_codes("stable") == "保持平稳"
    assert translate_inline_codes("improving") == "持续向好"


def test_audit9_multi_agent_prompts_forbid_markdown_stars_and_handle_solo_action():
    assert "不使用星号加粗" in multi_agent.ROLE_REGISTRY["analysis"].system_prompt
    assert "单人模式" in multi_agent.ROLE_REGISTRY["action"].system_prompt

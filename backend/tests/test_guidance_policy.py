from app.services.guidance_policy import build_guidance_policy
from app.services.product_prefs import normalize_product_prefs


def test_normalize_product_prefs_defaults_spiritual_support_to_disabled():
    prefs = normalize_product_prefs(None)

    assert prefs["preferred_language"] == "zh"
    assert prefs["tone_preference"] == "gentle"
    assert prefs["spiritual_support_enabled"] is False


def test_normalize_product_prefs_accepts_spiritual_support_opt_in():
    prefs = normalize_product_prefs({"spiritual_support_enabled": True})

    assert prefs["spiritual_support_enabled"] is True


def test_normalize_product_prefs_deduplicates_custom_mood_presets():
    prefs = normalize_product_prefs(
        {
            "custom_mood_presets": [
                "失落",
                "  释然  ",
                "失落",
                "",
                "心里堵堵的；",
            ]
        }
    )

    assert prefs["custom_mood_presets"] == ["失落", "释然", "心里堵堵的"]


def test_normalize_product_prefs_limits_hidden_default_moods_to_known_tags():
    prefs = normalize_product_prefs(
        {
            "hidden_default_moods": [
                "焦虑",
                "  生气  ",
                "焦虑",
                "释然",
                "",
            ]
        }
    )

    assert prefs["hidden_default_moods"] == ["焦虑", "生气"]


def test_guidance_policy_allows_spiritual_content_only_after_opt_in_in_stable_state():
    policy = build_guidance_policy(
        stable_profile={
            "preferred_language": "zh",
            "tone_preference": "gentle",
            "spiritual_support_enabled": True,
        },
        recent_baseline={
            "metrics": {
                "alignment_avg_score": 84,
                "interaction_overlap_rate": 0.72,
                "crisis_event_count": 0,
            },
            "risk": {"current_level": "none", "trend": "stable"},
        },
        risk_status={"risk_level": "none", "trend": "stable"},
        scope_type="pair",
        current_input={"text": "今天总体还算稳定，我们只是想看看怎么更懂彼此。"},
    )

    assert policy["response_language"] == "zh-CN"
    assert policy["safety_mode"] == "normal"
    assert policy["spiritual_content_enabled_by_user"] is True
    assert policy["spiritual_content_allowed_now"] is True
    assert policy["crisis_response_required"] is False


def test_guidance_policy_disables_spiritual_content_at_moderate_risk():
    policy = build_guidance_policy(
        stable_profile={
            "preferred_language": "zh",
            "tone_preference": "gentle",
            "spiritual_support_enabled": True,
        },
        recent_baseline={
            "metrics": {
                "alignment_avg_score": 77,
                "interaction_overlap_rate": 0.58,
            },
            "risk": {"current_level": "moderate", "trend": "declining"},
        },
        risk_status={"risk_level": "moderate", "trend": "declining"},
        scope_type="pair",
        current_input={"text": "最近说着说着就很容易卡住。"},
    )

    assert policy["safety_mode"] == "cautious"
    assert policy["spiritual_content_allowed_now"] is False
    assert "风险" in policy["spiritual_content_reason"]


def test_guidance_policy_routes_to_official_channels_when_dangerous_content_is_detected():
    policy = build_guidance_policy(
        stable_profile={
            "preferred_language": "zh",
            "tone_preference": "gentle",
            "spiritual_support_enabled": True,
        },
        recent_baseline={
            "metrics": {"alignment_avg_score": 40, "crisis_event_count": 2},
            "risk": {"current_level": "moderate", "trend": "declining"},
        },
        risk_status={"risk_level": "moderate", "trend": "declining"},
        scope_type="pair",
        current_input={"text": "他刚刚威胁我，还打我，我现在不敢回家。"},
    )

    crisis_support = policy["crisis_support"]

    assert policy["safety_mode"] == "protective"
    assert policy["crisis_response_required"] is True
    assert crisis_support is not None
    assert "110" in {item["id"] for item in crisis_support["channels"]}
    assert "12110" in {item["id"] for item in crisis_support["channels"]}
    assert "120" in {item["id"] for item in crisis_support["channels"]}
    assert "安全" in crisis_support["urgent_message"]

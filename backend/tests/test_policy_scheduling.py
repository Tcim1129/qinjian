from app.services.policy_scheduling import (
    _base_cycle_days,
    _schedule_mode,
    build_policy_schedule_preview,
)


def test_base_cycle_days_caps_high_risk_cycles():
    assert _base_cycle_days(
        plan_type="distance_compensation_plan",
        intensity="stretch",
        risk_now="moderate",
    ) == 3


def test_schedule_mode_switches_immediately_for_high_risk_or_backoff():
    assert (
        _schedule_mode(
            selection_mode="backoff_to_lower_friction",
            comparison_status=None,
            current_policy={"intensity": "steady", "observation_count": 1},
            recommended_policy=None,
            scorecard={"risk_now": "none"},
        )
        == "backoff_now"
    )
    assert (
        _schedule_mode(
            selection_mode=None,
            comparison_status="similar_to_baseline",
            current_policy={"intensity": "steady", "observation_count": 1},
            recommended_policy=None,
            scorecard={"risk_now": "severe"},
        )
        == "backoff_now"
    )


def test_policy_schedule_preview_exposes_transition_plan():
    preview = build_policy_schedule_preview(
        scorecard={
            "plan_type": "low_connection_recovery",
            "risk_now": "none",
            "completion_rate": 0.4,
            "usefulness_avg": 3.5,
            "friction_avg": 2.0,
        },
        strategy={
            "intensity": "steady",
            "policy_selection": {
                "mode": "adopt_proven_variant",
                "evidence_observation_count": 1,
                "current_policy_signature": "steady-clear-v1",
                "selected_policy_signature": "steady-gentle-v2",
            },
            "experiment_summary": {"comparison_status": "better_than_baseline"},
        },
    )

    assert preview is not None
    assert preview["schedule_mode"] == "finish_current_then_switch"
    assert preview["days_total"] == 4
    assert preview["min_observations"] == 3
    assert preview["days_remaining"] >= 0

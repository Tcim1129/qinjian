from app.services.behavior_judgement import (
    apply_judgement_to_payload,
    judge_behavior_against_baseline,
    make_behavior_observation,
    summarize_text_emotion,
    summarize_behavior_profile,
)


def test_judge_behavior_returns_insufficient_history_when_samples_are_too_few():
    baseline = summarize_behavior_profile(
        [
            make_behavior_observation(
                source="checkin",
                event_type="checkin.created",
                text="我今天有点委屈，但还是想好好说。",
            )
        ]
    )

    result = judge_behavior_against_baseline(
        "我只是想把事情说清楚。",
        baseline_summary=baseline,
    )

    assert result["baseline_match"] == "insufficient_history"
    assert result["reaction_shift"] == "unknown"
    assert result["deviation_reasons"] == []


def test_judge_behavior_detects_strong_deviation_against_stable_baseline():
    observations = [
        make_behavior_observation(
            source="checkin",
            event_type="checkin.created",
            text="我想和你慢慢说，我刚刚有点失落。",
        )
        for _ in range(8)
    ]
    baseline = summarize_behavior_profile(observations)

    result = judge_behavior_against_baseline(
        "你怎么又这样，我真的很烦，现在立刻回我。",
        baseline_summary=baseline,
        risk_level="high",
    )

    assert result["history_sufficiency"] == "sufficient"
    assert result["baseline_match"] == "strong_deviation"
    assert result["deviation_score"] >= 0.55
    assert result["deviation_reasons"]
    assert result["reaction_shift"] in {"more_defensive", "more_urgent", "shifted"}


def test_judge_behavior_returns_match_for_similar_style():
    observations = [
        make_behavior_observation(
            source="checkin",
            event_type="checkin.created",
            text="我想和你确认一下，等你有空的时候我们聊十分钟可以吗？",
        )
        for _ in range(8)
    ]
    baseline = summarize_behavior_profile(observations)

    result = judge_behavior_against_baseline(
        "我想先确认一下，等你方便的时候我们聊聊可以吗？",
        baseline_summary=baseline,
    )

    assert result["baseline_match"] == "match"
    assert result["reaction_shift"] == "stable"


def test_apply_judgement_to_payload_keeps_standardized_fields():
    judgement = judge_behavior_against_baseline(
        "你怎么又不回我。",
        baseline_summary=summarize_behavior_profile(
            [
                make_behavior_observation(
                    source="checkin",
                    event_type="checkin.created",
                    text="我想和你好好说。",
                )
                for _ in range(8)
            ]
        ),
        risk_level="watch",
    )

    payload = apply_judgement_to_payload(
        {
            "draft": "公司 token 是 CANARY_BEHAVIOR_CASE，手机号 13800138000。",
            "checkin_a_id": "123e4567-e89b-12d3-a456-426614174000",
        },
        text="你怎么又不回我。",
        risk_level="watch",
        judgement=judgement,
    )

    assert payload["inferred_tone"]
    assert payload["message_length_bucket"]
    assert payload["reaction_type"]
    assert payload["risk_level"] == "watch"
    assert payload["baseline_match"] == judgement["baseline_match"]
    assert "CANARY_BEHAVIOR_CASE" not in payload["draft"]
    assert "13800138000" not in payload["draft"]
    assert payload["checkin_a_id"] == "123e4567-e89b-12d3-a456-426614174000"


def test_summarize_text_emotion_returns_score_and_chinese_labels():
    summary = summarize_text_emotion("今天我只是希望对方能先听懂我的委屈。")

    assert summary["sentiment"] == "negative"
    assert summary["sentiment_label"] == "偏负向"
    assert summary["mood_label"] == "委屈"
    assert summary["display_mood_tags"] == ["委屈"]
    assert summary["emotion_profile"]["primary_mood"] == "委屈"
    assert summary["score"] >= 5
    assert "委屈" in summary["emotion_blend_summary"]


def test_summarize_text_emotion_skips_negated_emotion_and_marks_resolution_positive():
    summary = summarize_text_emotion("我现在已经不焦虑了，反而慢慢平静下来了。")

    assert summary["sentiment"] == "positive"
    assert summary["mood_label"] == "平静"
    assert summary["primary_mood"] == "平静"
    assert summary["secondary_moods"] == []
    assert "焦虑" not in summary["mood_tags"]


def test_summarize_text_emotion_keeps_multiple_moods_and_chooses_primary_by_weight():
    summary = summarize_text_emotion("我其实很累，但还是期待这周末能和你好好待一会儿。")

    assert summary["sentiment"] == "negative"
    assert summary["mood_label"] == "疲惫"
    assert summary["primary_mood"] == "疲惫"
    assert "期待" in summary["mood_tags"]
    assert "期待" in summary["secondary_moods"]
    assert summary["display_mood_tags"] == ["疲惫", "期待"]
    assert "疲惫" in summary["emotion_blend_summary"]
    assert summary["emotion_weights"][0]["tag"] == "疲惫"


def test_summarize_text_emotion_removes_negated_mood_from_results():
    summary = summarize_text_emotion("我不是生气，我只是很难过也有点委屈。")

    assert summary["mood_label"] == "委屈"
    assert summary["primary_mood"] == "委屈"
    assert "生气" not in summary["mood_tags"]

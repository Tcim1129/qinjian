from types import SimpleNamespace

from app.services.task_feedback import (
    _resolve_copy_mode,
    _score_feedback_style,
    summarize_feedback_map,
)


def test_summarize_feedback_map_aggregates_scores():
    summary = summarize_feedback_map(
        {
            "task-1": {"usefulness_score": 4, "friction_score": 2},
            "task-2": {"usefulness_score": 3, "friction_score": 3},
        }
    )

    assert summary == {
        "feedback_count": 2,
        "usefulness_avg": 3.5,
        "friction_avg": 2.5,
        "relationship_shift_avg": None,
    }


def test_feedback_style_prefers_gentle_copy_when_notes_repeat_it():
    events = [
        SimpleNamespace(
            payload={
                "usefulness_score": 3,
                "friction_score": 5,
                "note": "希望语气更温柔一点，也给个例子",
            }
        ),
        SimpleNamespace(
            payload={
                "usefulness_score": 4,
                "friction_score": 4,
                "note": "再温柔一点会更容易执行",
            }
        ),
    ]

    scores = _score_feedback_style(events)

    assert scores["gentle"] > scores["example"]
    assert _resolve_copy_mode(scores, feedback_count=2) == "gentle"

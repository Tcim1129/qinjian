"""Lightweight replay helpers for relationship decision evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.relationship_algorithms import (
    build_alignment_baseline,
    build_message_preview_baseline,
)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    task: str
    input_payload: dict
    expected: dict


EVALUATION_CASES: list[EvaluationCase] = [
    EvaluationCase(
        case_id="message-high-risk-1",
        task="message_simulation",
        input_payload={"draft": "你每次都这样，我真的懒得再解释了。", "context": {}},
        expected={"risk_level": "high", "baseline_match": "strong_deviation"},
    ),
    EvaluationCase(
        case_id="message-low-risk-1",
        task="message_simulation",
        input_payload={"draft": "我想确认一下，等你忙完后我们聊十分钟可以吗？", "context": {}},
        expected={"risk_level": "low"},
    ),
    EvaluationCase(
        case_id="alignment-misaligned-1",
        task="alignment",
        input_payload={
            "context": {},
            "checkin_a": {"content": "你昨天一直没回，我会慌。"},
            "checkin_b": {"content": "我昨天开会到很晚，回家只想先缓一下。"},
        },
        expected={"alignment_score_min": 40, "fallback": True},
    ),
]


def replay_message_case(case: EvaluationCase) -> dict:
    payload = build_message_preview_baseline(case.input_payload.get("draft", ""), case.input_payload.get("context") or {})
    return {
        "case_id": case.case_id,
        "task": case.task,
        "prediction": payload,
        "expected": case.expected,
    }


def replay_alignment_case(case: EvaluationCase) -> dict:
    payload = build_alignment_baseline(
        context=case.input_payload.get("context") or {},
        checkin_a=case.input_payload.get("checkin_a") or {},
        checkin_b=case.input_payload.get("checkin_b") or {},
    )
    return {
        "case_id": case.case_id,
        "task": case.task,
        "prediction": payload,
        "expected": case.expected,
    }


def replay_evaluation_cases() -> list[dict]:
    results: list[dict] = []
    for case in EVALUATION_CASES:
        if case.task == "message_simulation":
            results.append(replay_message_case(case))
        else:
            results.append(replay_alignment_case(case))
    return results

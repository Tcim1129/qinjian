from __future__ import annotations

import asyncio

from app.ai import narrative_alignment


def test_narrative_alignment_returns_fallback_when_ai_call_times_out(monkeypatch):
    async def slow_chat_completion(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return "{}"

    monkeypatch.setattr(narrative_alignment, "chat_completion", slow_chat_completion)
    monkeypatch.setattr(narrative_alignment, "ALIGNMENT_TIMEOUT_SECONDS", 0.01)

    result = asyncio.run(
        narrative_alignment.generate_narrative_alignment(
            context={},
            checkin_a={"content": "我觉得自己没有被认真听见。"},
            checkin_b={"content": "我其实是想先冷静一下再回应。"},
        )
    )

    assert 0 <= result["alignment_score"] <= 100
    assert result["shared_story"]
    assert result["source"] == "fallback"
    assert result["is_fallback"] is True
    assert result["raw_error"] == "TimeoutError"


def test_narrative_alignment_returns_fallback_when_ai_call_fails(monkeypatch):
    async def failing_chat_completion(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(narrative_alignment, "chat_completion", failing_chat_completion)

    result = asyncio.run(
        narrative_alignment.generate_narrative_alignment(
            context={},
            checkin_a={"content": "我觉得自己没有被认真听见。"},
            checkin_b={"content": "我其实是想先冷静一下再回应。"},
        )
    )

    assert 0 <= result["alignment_score"] <= 100
    assert result["suggested_opening"]
    assert result["source"] == "fallback"
    assert result["is_fallback"] is True
    assert result["raw_error"] == "RuntimeError"


def test_narrative_alignment_marks_successful_ai_payload(monkeypatch):
    async def ok_chat_completion(*_args, **_kwargs):
        return """
        {
          "alignment_score": 82,
          "shared_story": "双方都想把这次误会讲清楚。",
          "view_a_summary": "A方在意被认真回应。",
          "view_b_summary": "B方更想先缓一下再解释。",
          "misread_risk": "缓一下容易被听成不在乎。",
          "divergence_points": ["回应节奏不同"],
          "bridge_actions": ["先说清楚需要多久缓冲"],
          "suggested_opening": "我想先对齐一下我们刚才各自听见了什么。",
          "coach_note": "先确认理解，再讨论动作。"
        }
        """

    monkeypatch.setattr(narrative_alignment, "chat_completion", ok_chat_completion)

    result = asyncio.run(
        narrative_alignment.generate_narrative_alignment(
            context={},
            checkin_a={"content": "我觉得自己没有被认真听见。"},
            checkin_b={"content": "我其实是想先冷静一下再回应。"},
        )
    )

    assert 60 <= result["alignment_score"] <= 82
    assert result["shared_story"] == "双方都想把这次误会讲清楚。"
    assert result["source"] == "ai"
    assert result["is_fallback"] is False


def test_narrative_alignment_structured_fallback_reflects_current_checkins(monkeypatch):
    async def failing_chat_completion(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(narrative_alignment, "chat_completion", failing_chat_completion)

    result = asyncio.run(
        narrative_alignment.generate_narrative_alignment(
            context={},
            checkin_a={"label": "陈一", "content": "你昨天一直没回，我会慌，也会觉得自己像被晾着。"},
            checkin_b={"label": "林夏", "content": "我昨天开会到很晚，回家后只想先缓一下，不是不在乎。"},
        )
    )

    assert result["source"] == "fallback"
    assert result["is_fallback"] is True
    assert result["alignment_score"] != 61
    assert any(token in result["shared_story"] for token in ("没回", "回应", "缓一下", "不在乎"))
    assert any(token in result["misread_risk"] for token in ("听成", "误会", "不在乎", "压力"))

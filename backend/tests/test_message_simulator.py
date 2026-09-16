from __future__ import annotations

import asyncio
import json

import pytest

from app.ai import message_simulator


def test_message_simulator_timeout_stays_within_user_facing_minute_limit():
    assert 55 <= message_simulator.SIMULATION_TIMEOUT_SECONDS <= 60


def test_message_simulator_fallback_rewrites_instead_of_echoing_draft(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        return "not json"

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    result = asyncio.run(message_simulator.simulate_message_preview(draft, {}))

    assert result["safer_rewrite"] != draft
    assert "我" in result["safer_rewrite"]


def test_message_simulator_replaces_echoed_safer_rewrite(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"
    echoed_payload = {
        "partner_view": "对方会感到被责备。",
        "likely_impact": "可能升级冲突。",
        "risk_level": "medium",
        "risk_reason": "带有绝对化指责。",
        "safer_rewrite": draft,
        "suggested_tone": "先表达感受",
        "conversation_goal": "降低防御",
        "do_list": ["说感受"],
        "avoid_list": ["避免绝对化"],
    }

    async def fake_chat_completion(*_args, **_kwargs):
        return json.dumps(echoed_payload, ensure_ascii=False)

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    result = asyncio.run(message_simulator.simulate_message_preview(draft, {}))

    assert result["safer_rewrite"] != draft
    assert result["risk_level"] == "high"


def test_message_simulator_returns_fallback_when_ai_call_fails(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    result = asyncio.run(message_simulator.simulate_message_preview(draft, {}))

    assert result["safer_rewrite"] != draft
    assert result["risk_level"] == "high"
    assert result["risk_level_label"] == "高风险"
    assert result["raw_error"] == "RuntimeError"
    assert result["algorithm_version"]
    assert result["confidence"] is not None
    assert result["decision_trace"]["layer"] == "message_simulation"
    assert result["feedback_status"] == "pending_feedback"


def test_message_simulator_raises_timeout_instead_of_returning_fallback(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return "{}"

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(message_simulator, "SIMULATION_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(message_simulator.simulate_message_preview(draft, {}))


def test_message_simulator_keeps_gentle_clarifying_draft_at_low_risk_when_ai_fails(monkeypatch):
    draft = "我想确认一下，等你忙完后我们聊十分钟可以吗？"

    async def fake_chat_completion(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    result = asyncio.run(message_simulator.simulate_message_preview(draft, {}))

    assert result["risk_level"] == "low"
    assert "确认" in result["conversation_goal"] or "聊" in result["conversation_goal"]
    assert "每次都" not in result["safer_rewrite"]

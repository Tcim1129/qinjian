from __future__ import annotations

import asyncio
import json

import pytest

from app.ai import message_simulator


def test_message_simulator_timeout_stays_within_user_facing_minute_limit():
    assert 55 <= message_simulator.SIMULATION_TIMEOUT_SECONDS <= 60


@pytest.mark.parametrize('response', ['not json', '{}', '[]', 'null', '', '{"safer_rewrite":""}'])
def test_message_simulator_rejects_invalid_output_without_template(monkeypatch, response):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        return response

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    with pytest.raises(message_simulator.MessageSimulationUnavailableError):
        asyncio.run(message_simulator.simulate_message_preview(draft, {}))


def test_message_simulator_keeps_model_text_and_deterministic_risk_floor(monkeypatch):
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

    assert result["safer_rewrite"] == draft
    assert result["risk_level"] == "high"
    assert result["fallback_reason"] is None


def test_message_simulator_raises_safe_error_when_ai_call_fails(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    with pytest.raises(message_simulator.MessageSimulationUnavailableError) as error:
        asyncio.run(message_simulator.simulate_message_preview(draft, {}))
    assert 'upstream unavailable' not in str(error.value)


def test_message_simulator_raises_timeout_instead_of_returning_fallback(monkeypatch):
    draft = "你每次都这样，我真的懒得再解释了。"

    async def fake_chat_completion(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return "{}"

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(message_simulator, "SIMULATION_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(message_simulator.simulate_message_preview(draft, {}))


def test_message_simulator_keeps_suitable_original_without_forcing_a_rewrite(monkeypatch):
    draft = "我想确认一下，等你忙完后我们聊十分钟可以吗？"

    async def fake_chat_completion(*_args, **_kwargs):
        return json.dumps({
            'partner_view': '这是一次时间确认。', 'likely_impact': '可以留出回应空间。',
            'risk_level': 'low', 'risk_reason': '措辞清楚，没有指责。',
            'safer_rewrite': draft, 'suggested_tone': '平静', 'conversation_goal': '确认聊天时间',
            'do_list': [], 'avoid_list': [], 'confidence': 1, 'algorithm_version': 'model-invented',
        }, ensure_ascii=False)

    monkeypatch.setattr(message_simulator, "chat_completion", fake_chat_completion)

    result = asyncio.run(message_simulator.simulate_message_preview(draft, {}))

    assert result["risk_level"] == "low"
    assert result["safer_rewrite"] == draft
    assert result['do_list'] == []
    assert result['avoid_list'] == []
    assert result['algorithm_version'] != 'model-invented'


@pytest.mark.parametrize('failure,status', [('provider', 502), ('timeout', 504)])
def test_simulation_route_exposes_failure_without_creating_success_event(monkeypatch, failure, status):
    from contextlib import nullcontext
    from types import SimpleNamespace
    import uuid
    from fastapi import HTTPException
    from app.api.v1 import agent
    from app.schemas import MessageSimulationRequest

    async def noop(*args, **kwargs):
        return SimpleNamespace(behavior_summary={})

    async def fail(*args, **kwargs):
        if failure == 'timeout':
            raise asyncio.TimeoutError()
        raise message_simulator.MessageSimulationUnavailableError('safe failure')

    async def unexpected(*args, **kwargs):
        pytest.fail('A failed model call must not create a successful simulation event')

    monkeypatch.setattr(agent, 'consume_request_cooldown', noop)
    monkeypatch.setattr(agent, 'refresh_profile_snapshot', noop)
    monkeypatch.setattr(agent, '_simulation_solo_context', lambda *args: {})
    monkeypatch.setattr(agent, 'privacy_audit_scope', lambda **kwargs: nullcontext())
    monkeypatch.setattr(agent, 'simulate_message_preview', fail)
    monkeypatch.setattr(agent, 'record_relationship_event', unexpected)
    user = SimpleNamespace(id=uuid.uuid4(), product_prefs={}, email='expression-test@example.invalid')
    with pytest.raises(HTTPException) as error:
        asyncio.run(agent.simulate_message(MessageSimulationRequest(draft='今晚我想自己待会儿。'), None, user, SimpleNamespace(commit=noop)))
    assert error.value.status_code == status

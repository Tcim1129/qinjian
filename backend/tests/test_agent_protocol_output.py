import asyncio
from types import SimpleNamespace

import pytest
from app.ai import agent_loop


def response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))])


def test_internal_tool_markup_retries_without_showing_or_executing_it(monkeypatch):
    calls = []

    async def complete(**kwargs):
        calls.append(kwargs)
        return response('<｜DSML｜ calls>内部工具标记</｜DSML｜ calls>' if len(calls) == 1 else '今天工作后有点累，可以先歇一会儿。')

    monkeypatch.setattr(agent_loop, 'create_chat_completion', complete)
    reply, steps, _ = asyncio.run(agent_loop.run_agent_loop(
        [{'role': 'user', 'content': '今天工作后有点累。'}], allowed_tool_names=['get_recent_events'], max_steps=3))
    assert len(calls) == 2
    assert all(not call['tools'] for call in calls)
    assert 'DSML' not in reply
    assert not any(step.tool_calls for step in steps)
    assert '没有可用工具' in calls[-1]['messages'][-1]['content']


def test_repeated_internal_markup_is_a_failed_role_instead_of_success(monkeypatch):
    async def complete(**kwargs):
        return response('<｜DSML｜ calls>内部标记</｜DSML｜ calls>')

    monkeypatch.setattr(agent_loop, 'create_chat_completion', complete)
    with pytest.raises(ValueError, match='正文'):
        asyncio.run(agent_loop.run_agent_loop(
            [{'role': 'user', 'content': '今天工作后有点累。'}], allowed_tool_names=[], max_steps=3))

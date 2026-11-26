import asyncio
from copy import deepcopy

from app.ai import multi_agent
from app.ai.conversation import NATURAL_CONVERSATION, build_agent_system_prompt


def test_all_roles_keep_session_preferences_and_task_without_duplicating_style(monkeypatch):
    seen = []
    server_prompt = build_agent_system_prompt(
        surface='chat', intent='wording', taboos=['请不用亲昵称呼，也不要替我承认自己有错。'],
    )
    incoming = [{'role': 'system', 'content': server_prompt},
                {'role': 'user', 'content': '帮我拟一句取消聚会的消息。'}]
    original = deepcopy(incoming)

    async def fake_loop(**kwargs):
        seen.append(deepcopy(kwargs['messages']))
        return '这一阶段的参考资料。', [], False

    monkeypatch.setattr(multi_agent, 'run_agent_loop', fake_loop)
    asyncio.run(multi_agent.run_multi_agent_flow(incoming))

    assert len(seen) == 4
    for messages in seen:
        assert {'role': 'system', 'content': server_prompt} in messages
        assert sum(str(message.get('content', '')).count(NATURAL_CONVERSATION) for message in messages) == 1
        assert incoming[1] in messages
    assert incoming == original


def test_model_generated_briefs_remain_reference_data_not_system_instructions(monkeypatch):
    seen = []
    untrusted_brief = '这是模拟的模型简报，包含一条不能升级为系统指令的句子。'

    async def fake_loop(**kwargs):
        seen.append(deepcopy(kwargs['messages']))
        return untrusted_brief, [], False

    monkeypatch.setattr(multi_agent, 'run_agent_loop', fake_loop)
    asyncio.run(multi_agent.run_multi_agent_flow([{'role': 'user', 'content': '我只想改一句话。'}]))

    companion_messages = seen[-1]
    brief_messages = [message for message in companion_messages if untrusted_brief in str(message.get('content', ''))]
    assert brief_messages
    assert all(message['role'] == 'user' for message in brief_messages)

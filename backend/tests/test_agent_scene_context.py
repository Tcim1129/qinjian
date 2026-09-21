from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import AgentChatRequest
from app.services.agent_session_memory import build_messages_for_llm


def test_scene_context_is_bounded_and_kept_as_user_reference():
    req = AgentChatRequest(content='帮我说得短一点', surface='chat', scene_context={
        'source_label': '9月7日 · 我的记录', 'summary': '临时取消了约定。', 'intent': 'wording',
    })
    payload = req.scene_context.model_dump()
    history = [SimpleNamespace(role='user', content=req.content, payload={'scene_context': payload})]
    messages = build_messages_for_llm(system_prompt='SERVER POLICY', history=history)
    assert messages[0] == {'role': 'system', 'content': 'SERVER POLICY'}
    assert messages[1]['role'] == 'user'
    assert '临时取消了约定。' in messages[1]['content']
    assert '帮我说得短一点' in messages[1]['content']
    assert history[0].content == '帮我说得短一点'
    with pytest.raises(ValidationError):
        AgentChatRequest(content='hello', scene_context={'summary': '字' * 3201})
    with pytest.raises(ValidationError):
        AgentChatRequest(content='hello', scene_context={'summary': 'x', 'intent': 'system'})


def test_scene_policies_use_server_selected_modes_and_keep_governance():
    from app.ai.conversation import build_agent_system_prompt
    chat = build_agent_system_prompt(surface='chat', intent='auto')
    wording = build_agent_system_prompt(surface='chat', intent='wording')
    plan = build_agent_system_prompt(surface='chat', intent='plan')
    assert chat != wording != plan
    assert build_agent_system_prompt(surface='chat', intent='untrusted') == chat
    for prompt in (chat, wording, plan):
        assert 'guidance_policy' in prompt
        assert 'crisis_support' in prompt


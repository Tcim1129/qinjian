from app.ai.policy import compose_relationship_system_prompt


def test_relationship_policy_prompt_enforces_chinese_and_safe_routing():
    prompt = compose_relationship_system_prompt("你是关系支持助手。")

    assert prompt.startswith("你是关系支持助手。")
    assert "简体中文" in prompt
    assert "温柔" in prompt
    assert "塔罗" in prompt
    assert "星座" in prompt
    assert "110" in prompt
    assert "12110" in prompt
    assert "12356" in prompt
    assert "操控" in prompt

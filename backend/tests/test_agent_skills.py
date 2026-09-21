"""测试 Agent Skill 注册表、依赖编排与交付物组装。"""

import pytest
from app.ai.skill_registry import (
    SKILL_REGISTRY,
    SkillDefinition,
    SkillOutput,
    resolve_execution_order,
    execute_skill,
)
from app.ai.skill_delivery import (
    assemble_delivery_package,
    ProblemSummary,
    StanceCard,
    ActionProposal,
    CommunicationDraft,
    ReviewTask,
    SkillStep,
)
from app.ai.skill_orchestrator import OrchestrationPlan, judge_complexity, generate_draft_for_proposal


def test_all_seven_skills_registered():
    expected_skills = [
        "expression_clarify",
        "stance_analysis",
        "conflict_detect",
        "action_plan",
        "draft_message",
        "review",
        "memory_write",
    ]
    for skill_name in expected_skills:
        assert skill_name in SKILL_REGISTRY, f"Missing skill: {skill_name}"
        skill = SKILL_REGISTRY[skill_name]
        assert skill.label, f"Skill {skill_name} must have a label"
        assert skill.description, f"Skill {skill_name} must have a description"
        assert callable(skill.handler), f"Skill {skill_name} handler must be callable"


def test_resolve_execution_order_dependencies():
    # 测试有依赖关系的拓扑排序
    # action_plan 依赖 conflict_detect -> stance_analysis -> expression_clarify
    order = resolve_execution_order(["action_plan"])
    assert "expression_clarify" in order
    assert "stance_analysis" in order
    assert "conflict_detect" in order
    assert "action_plan" in order

    # 依赖顺序必须满足：expression_clarify 在 stance_analysis 之前，stance_analysis 在 conflict_detect 之前
    idx_clarify = order.index("expression_clarify")
    idx_stance = order.index("stance_analysis")
    idx_conflict = order.index("conflict_detect")
    idx_action = order.index("action_plan")

    assert idx_clarify < idx_stance < idx_conflict < idx_action


def test_resolve_execution_order_circular_detection():
    # 模拟循环依赖抛错
    test_skills = {
        "a": SkillDefinition("a", "A", "desc", None, depends_on=["b"]),
        "b": SkillDefinition("b", "B", "desc", None, depends_on=["a"]),
    }
    from unittest.mock import patch
    with patch.dict(SKILL_REGISTRY, test_skills, clear=False):
        with pytest.raises(ValueError) as exc:
            resolve_execution_order(["a"])
        assert "Skill 依赖存在循环" in str(exc.value)


def test_memory_write_scheduled_last_and_independent_skills_parallel():
    # memory_write 是聚合器，必须排在所有分析类 skill 之后
    from app.ai.skill_orchestrator import _plan_execution_levels

    levels = _plan_execution_levels([
        "expression_clarify", "stance_analysis", "conflict_detect",
        "action_plan", "memory_write",
    ])
    flat = [name for level in levels for name in level]
    assert flat[-1] == "memory_write"
    assert flat.index("expression_clarify") < flat.index("stance_analysis")

    # review 预设中 expression_clarify 与 review 无依赖，应在同一层并行
    review_levels = _plan_execution_levels(["expression_clarify", "review", "memory_write"])
    assert set(review_levels[0]) == {"expression_clarify", "review"}
    assert review_levels[1] == ["memory_write"]


@pytest.mark.asyncio
async def test_memory_write_receives_all_previous_results(monkeypatch):
    # 端到端验证编排：记忆提取的输入必须包含全部分析结果（回归 memory_write 提前执行的 bug）
    captured = {}

    async def fake_chat(model, messages, temperature=0.7, **kwargs):
        text = messages[-1]["content"]
        if "分析结果" in text:
            captured["memory_input"] = text
            return '{"memories": [{"type": "event", "subject": "测试事件", "content": "内容", "importance": 3}]}'
        return '{"ok": true}'

    monkeypatch.setattr("app.ai.skills.chat_completion", fake_chat)
    monkeypatch.setattr("app.ai.skill_orchestrator.chat_completion", fake_chat)

    from app.ai.skill_orchestrator import orchestrate
    package = await orchestrate("我们因为旅行改期吵了一架")

    assert package.memories_to_save
    assert package.memories_to_save[0]["subject"] == "测试事件"
    for name in ("expression_clarify", "stance_analysis", "conflict_detect", "action_plan"):
        assert f'"{name}"' in captured["memory_input"], f"memory_write 缺少 {name} 的结果"


@pytest.mark.asyncio
async def test_orchestrate_with_known_intent_skips_complexity_judge(monkeypatch):
    # 调用方已给意图时，不应再多花一次 LLM 做意图判断
    invocations = []

    async def fake_chat(model, messages, temperature=0.7, **kwargs):
        invocations.append(messages[-1]["content"])
        return '{"ok": true}'

    monkeypatch.setattr("app.ai.skills.chat_completion", fake_chat)
    monkeypatch.setattr("app.ai.skill_orchestrator.chat_completion", fake_chat)

    from app.ai.skill_orchestrator import orchestrate
    package = await orchestrate("对方一直不回消息", intent="listen")

    assert package.primary_intent == "listen"
    assert [step.skill_name for step in package.skill_trace] == ["expression_clarify", "memory_write"]
    # 没有任何一次调用是"意图判断"（判断器的输入是原始文本本身）
    assert invocations, "应至少执行了 skill"
    assert all(call != "对方一直不回消息" for call in invocations)


@pytest.mark.asyncio
async def test_execute_skill_timeout_and_error_handling():
    import asyncio

    async def slow_handler(context, previous_results):
        await asyncio.sleep(0.5)
        return {"done": True}

    slow_skill = SkillDefinition(
        name="test_slow",
        label="慢速测试",
        description="测试超时",
        handler=slow_handler,
        max_timeout=0.05,
    )

    output = await execute_skill(slow_skill, context={}, previous_results={})
    assert not output.success
    assert "处理超时" in (output.error or "")

    async def broken_handler(context, previous_results):
        raise RuntimeError("模拟异常")

    broken_skill = SkillDefinition(
        name="test_broken",
        label="异常测试",
        description="测试异常",
        handler=broken_handler,
        max_timeout=2.0,
    )

    output2 = await execute_skill(broken_skill, context={}, previous_results={})
    assert not output2.success
    assert "模拟异常" in (output2.error or "")


def test_assemble_delivery_package():
    plan = OrchestrationPlan(
        is_complex=True,
        primary_intent="resolve",
        skill_names=["expression_clarify", "stance_analysis", "conflict_detect", "action_plan", "memory_write"],
        execution_order=["expression_clarify", "stance_analysis", "conflict_detect", "action_plan", "memory_write"],
        reason="复杂矛盾事件",
    )

    results = {
        "expression_clarify": SkillOutput(
            skill_name="expression_clarify",
            success=True,
            data={
                "people": [{"name": "小美", "role": "伴侣", "emotion": "委屈"}],
                "events": [{"description": "旅行取消", "time": "上周", "importance": "high"}],
                "user_emotion": "失落",
                "core_need": "需要被重视",
            },
        ),
        "stance_analysis": SkillOutput(
            skill_name="stance_analysis",
            success=True,
            data={
                "stances": [
                    {
                        "person": "我",
                        "position": "希望如期出发",
                        "underlying_need": "重视陪伴",
                        "worry": "被忽略",
                        "flexibility": "medium",
                    },
                    {
                        "person": "小美",
                        "position": "工作太累想改期",
                        "underlying_need": "需要休息",
                        "worry": "无法胜任工作",
                        "flexibility": "low",
                    },
                ],
                "common_ground": "都珍惜假期",
                "core_tension": "精力有限 vs 陪伴期望",
            },
        ),
        "conflict_detect": SkillOutput(
            skill_name="conflict_detect",
            success=True,
            data={
                "has_conflict": True,
                "conflict_type": "期望落差",
                "severity": "medium",
                "priority_issue": "先确认双方真实精力状态再安排行程",
            },
        ),
        "action_plan": SkillOutput(
            skill_name="action_plan",
            success=True,
            data={
                "proposals": [
                    {
                        "id": "A",
                        "title": "推迟一周但安排近郊轻度假",
                        "description": "给对方充分休息时间，同时保留轻度陪伴",
                        "approach": "gentle",
                        "pros": ["兼顾休息与陪伴"],
                        "cons": ["需要改签"],
                        "effort": "low",
                        "recommended": True,
                    }
                ]
            },
        ),
        "memory_write": SkillOutput(
            skill_name="memory_write",
            success=True,
            data={
                "memories": [
                    {
                        "type": "event",
                        "subject": "旅行改期争执",
                        "content": "因工作压力希望改期，用户易感到被忽略",
                        "importance": 4,
                    }
                ]
            },
        ),
    }

    steps = [
        SkillStep(skill_name="expression_clarify", skill_label="表达澄清", status="ok", duration_ms=120.0),
        SkillStep(skill_name="stance_analysis", skill_label="立场分析", status="ok", duration_ms=150.0),
        SkillStep(skill_name="conflict_detect", skill_label="冲突识别", status="ok", duration_ms=110.0),
        SkillStep(skill_name="action_plan", skill_label="行动规划", status="ok", duration_ms=200.0),
        SkillStep(skill_name="memory_write", skill_label="关系记忆", status="ok", duration_ms=90.0),
    ]

    pkg = assemble_delivery_package(
        results=results,
        skill_steps=steps,
        plan=plan,
        total_duration_ms=670.0,
    )

    data = pkg.to_dict()
    assert data["primary_intent"] == "resolve"
    assert data["is_complex"] is True
    assert len(data["summary"]["people"]) == 1
    assert data["summary"]["people"][0]["name"] == "小美"
    assert data["summary"]["priority_issue"] == "先确认双方真实精力状态再安排行程"
    assert len(data["stances"]) == 2
    assert data["stances"][0]["person"] == "我"
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["id"] == "A"
    assert data["proposals"][0]["recommended"] is True
    assert len(data["memories_to_save"]) == 1
    assert data["memories_to_save"][0]["subject"] == "旅行改期争执"
    assert len(data["skill_trace"]) == 5

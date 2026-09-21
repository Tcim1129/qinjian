"""Agent 工具注册表 — 将现有服务层包装为 Function Calling 工具

统一约定：handler 的签名尽量为 `(db, *, pair_id, user_id, **args)`，
由 execute_tool 注入 db / pair_id / user_id，args 来自模型的 tool_calls 参数。
"""

import asyncio
import logging
import uuid
from datetime import date
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_
from app.api.deps import validate_pair_access
from app.core.time import current_local_date

from app.services.crisis_processor import (
    CrisisAlert,
    select,
)
from app.services.safety_summary import build_safety_status
from app.services.intervention_evaluation import build_intervention_evaluation
from app.services.behavior_judgement import build_behavior_signal
from app.services.relationship_algorithms import build_message_preview_baseline
from app.services.timeline_archive import list_archive_checkins, list_archive_reports, serialize_archive_checkin_item, serialize_archive_report_item
from app.models import RelationshipTask, TaskStatus, User

logger = logging.getLogger(__name__)


def _normalize_crisis_level(level: Any) -> str:
    """把各种危机等级表示统一为 low / medium / high / severe。"""
    text = str(level or "").upper()
    if "SEVERE" in text or text in ("SEVERE", "CRITICAL", "HIGH", "RED"):
        return "severe"
    if text in ("MODERATE", "MEDIUM", "MID"):
        return "medium"
    if text in ("MILD", "LOW", "NONE"):
        return "low"
    if "HIGH" in text:
        return "high"
    return text.lower() if text else "low"


def _normalize_uuid_param(value):
    """把 str / UUID 统一成 uuid.UUID；None 或非法字符串保持原样。"""
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError, AttributeError):
            return value
    return value


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: dict
    handler: Callable
    needs_db: bool = True
    needs_pair_id: bool = True
    needs_user_id: bool = False
    category: str = "perception"


TOOL_REGISTRY: dict[str, AgentTool] = {}


def register_tool(tool: AgentTool) -> AgentTool:
    TOOL_REGISTRY[tool.name] = tool
    return tool


# 感知层 (Perception)

async def _get_relationship_status(db, *, pair_id, user_id=None, **kwargs):
    """当前关系的全景安全/健康状态。"""
    snapshot = await build_safety_status(db=db, pair_id=pair_id, user_id=user_id)
    if isinstance(snapshot, dict):
        return snapshot.get("summary") or snapshot.get("report") or snapshot
    return {"status": "ok", "detail": str(snapshot) if snapshot else None}


async def _get_recent_events(db, *, pair_id, user_id=None, limit=10, **kwargs):
    """近期关系事件/打卡。"""
    try:
        limit = max(1, min(int(limit or 10), 50))
    except (TypeError, ValueError):
        limit = 10
    rows = await list_archive_checkins(
        db=db, pair_id=pair_id, user_id=user_id, limit=limit
    )
    return [_visible_checkin(row, user_id) for row in rows[:limit]]


def _visible_checkin(row, user_id):
    item = serialize_archive_checkin_item(row, actor_user_id=user_id)
    return {
        'id': str(item['id']),
        'type': item['item_type'],
        'text': str((item.get('record') or {}).get('content') or item['summary'])[:1000],
        'created_at': str(item['occurred_at']),
        'visibility': item['visibility'],
    }


async def _get_crisis_status(db, *, pair_id, user_id=None, **kwargs):
    """当前是否有未解决的危机预警及其等级。"""
    from app.services.crisis_processor import CrisisAlertStatus as CAS
    normalized_pair_id = _normalize_uuid_param(pair_id)
    result = await db.execute(
        select(CrisisAlert)
        .where(
            CrisisAlert.pair_id == normalized_pair_id,
            CrisisAlert.status == CAS.ACTIVE.value,
        )
        .order_by(CrisisAlert.created_at.desc())
        .limit(5)
    )
    rows = result.scalars().all()
    active = [r for r in rows if r.level is not None]
    return {
        "active_alerts": len(active),
        "highest_level": max((_normalize_crisis_level(r.level) for r in active), default="low"),
    }


async def _get_active_tasks(db, *, pair_id, user_id=None, **kwargs):
    """当前进行中的行动任务。"""
    normalized_pair_id = _normalize_uuid_param(pair_id)
    result = await db.execute(
        select(RelationshipTask)
        .where(
            RelationshipTask.pair_id == normalized_pair_id,
            RelationshipTask.status == TaskStatus.PENDING.value,
            or_(RelationshipTask.user_id.is_(None), RelationshipTask.user_id == _normalize_uuid_param(user_id)),
        )
        .order_by(RelationshipTask.created_at.desc())
        .limit(20)
    )
    tasks = []
    for t in result.scalars().all():
        tasks.append({"id": str(t.id), "title": t.title, "status": t.status, "due_date": str(t.due_date)})
    return tasks


async def _get_task_feedback(db, *, pair_id, user_id=None, **kwargs):
    from datetime import timedelta
    from app.services.task_feedback import get_latest_task_feedback_map
    feedback = await get_latest_task_feedback_map(
        db, pair_id=pair_id, user_id=user_id,
        start_date=current_local_date() - timedelta(days=14), end_date=current_local_date(),
    )
    selected = list(feedback.items())[:8]
    normalized_ids = [_normalize_uuid_param(task_id) for task_id, _ in selected]
    lookup_ids = [task_id for task_id in normalized_ids if isinstance(task_id, uuid.UUID)]

    tasks_by_id: dict[uuid.UUID, RelationshipTask] = {}
    if lookup_ids:
        rows = await db.execute(
            select(RelationshipTask).where(RelationshipTask.id.in_(lookup_ids))
        )
        tasks_by_id = {row.id: row for row in rows.scalars().all()}

    actor_id = _normalize_uuid_param(user_id)
    results = []
    for (task_id, item), normalized_id in zip(selected, normalized_ids):
        task = tasks_by_id.get(normalized_id) if isinstance(normalized_id, uuid.UUID) else None
        if not task or (task.user_id is not None and task.user_id != actor_id):
            continue
        results.append({'task_id': task_id, 'title': task.title, 'due_date': str(task.due_date),
            'status': task.status.value, **{key: item.get(key) for key in (
                'outcome', 'note', 'submitted_at', 'usefulness_score', 'friction_score', 'relationship_shift_score',
            )}})
    return results


async def _search_timeline(db, *, pair_id, user_id=None, query="", **kwargs):
    """按时间维度检索历史记录(打卡与报告)。"""
    keyword = str(query or "").strip()
    checkins = await list_archive_checkins(
        db=db, pair_id=pair_id, user_id=user_id, limit=24
    )
    reports = await list_archive_reports(
        db=db, pair_id=pair_id, user_id=user_id, limit=12
    )
    matches = []
    for c in checkins:
        visible = _visible_checkin(c, user_id)
        content = visible['text']
        if not keyword or keyword.lower() in content.lower():
            matches.append(visible)
    for r in reports:
        content = serialize_archive_report_item(r)['summary']
        if not keyword or keyword.lower() in content.lower():
            matches.append(
                {"type": "report", "text": content[:200], "created_at": str(getattr(r, "created_at", ""))}
            )
    return matches[:20]


register_tool(AgentTool(
    name="get_relationship_status",
    description="获取当前关系的全景安全与健康状态。当你需要先了解关系整体状况时调用。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=_get_relationship_status,
    needs_db=True,
    needs_pair_id=True,
))

register_tool(AgentTool(
    name="get_recent_events",
    description="获取近期(默认近10条)的关系记录，了解最近发生了什么。",
    parameters={
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "返回条数", "default": 10}},
        "required": [],
    },
    handler=_get_recent_events,
    needs_db=True,
    needs_pair_id=True,
))

register_tool(AgentTool(
    name="get_crisis_status",
    description="检查当前关系是否处于危机状态及最高危机等级。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=_get_crisis_status,
    needs_db=True,
    needs_pair_id=True,
))

register_tool(AgentTool(
    name="get_active_tasks",
    description="查看当前有哪些正在进行中的行动任务。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=_get_active_tasks,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
))

register_tool(AgentTool(
    name="get_task_feedback",
    description="查看本人最近14天行动的真实反馈，包括还没做、不太顺和有帮助。规划下一步时参考，不把未做当作失败，不重复已经解决的事。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=_get_task_feedback, needs_db=True, needs_pair_id=True, needs_user_id=True,
))

register_tool(AgentTool(
    name="search_timeline",
    description="检索历史记录(打卡与报告)，当需要回忆特定过去事件时调用。",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "搜索关键词"}},
        "required": ["query"],
    },
    handler=_search_timeline,
    needs_db=True,
    needs_pair_id=True,
))


async def _recall_relationship_memories(db, *, pair_id, user_id=None, query="", memory_type=None, limit=5, **kwargs):
    """主动检索跨会话的长期关系记忆。"""
    from app.services.relationship_memory import recall_memories
    types = [str(memory_type)] if memory_type else None
    return await recall_memories(
        db=db,
        pair_id=pair_id,
        user_id=user_id,
        query=str(query or ""),
        memory_types=types,
        limit=int(limit or 5),
    )


register_tool(AgentTool(
    name="recall_relationship_memories",
    description="主动检索跨会话的长期关系记忆（包括人物档案、过往冲突/事件、曾用沟通策略与相处模式）。当用户提起某人、过去某件事或需要参考历史经验时调用。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如人名、事件名或主题"},
            "memory_type": {"type": "string", "enum": ["person", "event", "strategy", "pattern"], "description": "记忆类型"},
            "limit": {"type": "integer", "description": "返回条数上限", "default": 5},
        },
        "required": [],
    },
    handler=_recall_relationship_memories,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
    category="perception",
))


# 分析层 (Reasoning)

def _analyze_behavior(db=None, *, pair_id=None, user_id=None, text="", **kwargs):
    return build_behavior_signal(text or None)


def _preview_message_risk(db=None, *, pair_id=None, user_id=None, draft_text="", **kwargs):
    return build_message_preview_baseline(draft_text or "")


async def _evaluate_intervention_need(db, *, pair_id, user_id=None, **kwargs):
    evaluation = await build_intervention_evaluation(
        db=db, pair_id=pair_id, user_id=user_id
    )
    if isinstance(evaluation, dict):
        return {
            "needed": evaluation.get("needs_intervention", evaluation.get("needed", False)),
            "urgency": evaluation.get("urgency", evaluation.get("risk_level", "monitor")),
            "recommendation": evaluation.get("recommendation", ""),
            "reason": evaluation.get("reason", ""),
        }
    return {"needed": False, "urgency": "monitor"}


register_tool(AgentTool(
    name="analyze_behavior",
    description="分析一段文字中的行为信号，返回情绪、冲突程度、压力分等。当用户描述对话或事件时调用。",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "需要分析的文字"}},
        "required": ["text"],
    },
    handler=_analyze_behavior,
    needs_db=False,
    needs_pair_id=False,
))

register_tool(AgentTool(
    name="preview_message_risk",
    description="预演草稿消息可能带来的风险，给出改进建议。当用户准备发送重要信息时调用。",
    parameters={
        "type": "object",
        "properties": {"draft_text": {"type": "string", "description": "草稿文本"}},
        "required": ["draft_text"],
    },
    handler=_preview_message_risk,
    needs_db=False,
    needs_pair_id=False,
))

register_tool(AgentTool(
    name="evaluate_intervention_need",
    description="评估当前关系状态是否需要干预，及紧急程度与推荐类型。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=_evaluate_intervention_need,
    needs_db=True,
    needs_pair_id=True,
))


async def _run_skill_analysis(db=None, *, pair_id=None, user_id=None, complex_event_text="", intent=None, **kwargs):
    """自主拆解并调用多个 Skill 模块对复杂关系矛盾做全套结构化分析。"""
    from app.ai.skill_orchestrator import orchestrate
    from app.services.relationship_memory import recall_memories
    memories = []
    if db is not None and pair_id is not None and user_id is not None:
        try:
            memories = await recall_memories(db, pair_id=pair_id, user_id=user_id, query=str(complex_event_text or ""), limit=5)
        except Exception:
            memories = []
    pkg = await orchestrate(
        str(complex_event_text or ""),
        pair_id=str(pair_id) if pair_id else None,
        user_id=str(user_id) if user_id else None,
        relationship_memories=memories,
        intent=str(intent) if intent else None,
    )
    return pkg.to_dict()


register_tool(AgentTool(
    name="run_skill_analysis",
    description="用户遇到复杂的关系矛盾时调用。分析用户想表达什么、双方的想法和争执原因，再整理结果并提出具体建议。",
    parameters={
        "type": "object",
        "properties": {
            "complex_event_text": {"type": "string", "description": "用户描述的复杂关系事件/冲突原文"},
            "intent": {
                "type": "string",
                "enum": ["listen", "clarify", "resolve", "plan", "review"],
                "description": "本次诉求意图，可省略；省略时由系统额外判断（更慢）",
            },
        },
        "required": ["complex_event_text"],
    },
    handler=_run_skill_analysis,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
    category="reasoning",
))


# 行动层 (Action)

async def _create_task(db, *, pair_id, user_id=None, title="", description="", due_date=None, **kwargs):
    """Models can propose only. The separate authenticated confirm endpoint writes tasks."""
    title = str(title or '').strip()
    if not title:
        raise ValueError('任务标题不能为空')
    target_date = date.fromisoformat(str(due_date)) if due_date else current_local_date()
    if target_date < current_local_date():
        raise ValueError('请选择今天或之后的日期')
    return {
        'proposal_id': str(uuid.uuid4()), 'title': title[:100],
        'description': str(description or '').strip()[:400],
        'due_date': target_date.isoformat(), 'requires_confirmation': True,
    }


register_tool(AgentTool(
    name="create_task",
    description="提出一个待用户确认的行动建议，不会保存任务。说明日期，只有用户点击加入安排后才创建；不要声称已安排。",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "任务标题"},
            "description": {"type": "string", "description": "任务描述"},
            "due_date": {"type": "string", "description": "计划日期 YYYY-MM-DD；省略为今天"},
        },
        "required": ["title", "description"],
    },
    handler=_create_task,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
))


async def _save_relationship_memory(db, *, pair_id, user_id=None, memory_type="event", subject="", content="", importance=3, **kwargs):
    """向跨会话长期关系知识库写入一条新记忆。"""
    from app.services.relationship_memory import store_memory
    mem = await store_memory(
        db,
        pair_id=pair_id,
        user_id=user_id,
        memory_type=str(memory_type or "event"),
        subject=str(subject or "").strip(),
        content={"detail": str(content or "").strip()},
        importance=int(importance or 3),
    )
    return {
        "status": "success",
        "memory_id": str(mem.id),
        "subject": mem.subject,
        "memory_type": mem.memory_type,
        "importance": mem.importance,
    }


register_tool(AgentTool(
    name="save_relationship_memory",
    description="保存重要的个人偏好、事件、约定和相处经验，供以后的对话参考。",
    parameters={
        "type": "object",
        "properties": {
            "memory_type": {"type": "string", "enum": ["person", "event", "strategy", "pattern"], "description": "记忆类型"},
            "subject": {"type": "string", "description": "记忆主题、人名或事件关键词（简明精准，10字以内）"},
            "content": {"type": "string", "description": "详细内容、共识或相处注意事项"},
            "importance": {"type": "integer", "description": "重要度 1-5（默认为3）", "default": 3},
        },
        "required": ["subject", "content"],
    },
    handler=_save_relationship_memory,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
    category="action",
))


# 打卡数据提取(保留兼容，实际由 agent.py 拦截处理)
extract_checkin_data_params = {
    "type": "object",
    "properties": {
        "diary_content": {"type": "string", "description": "替用户总结的日记正文"},
        "mood_score": {"type": "integer", "description": "心情分数 1-10"},
        "interaction_freq": {"type": "integer", "description": "关系互动频率 1-5"},
        "deep_conversation": {"type": "boolean", "description": "是否有深入对话反思"},
    },
    "required": ["diary_content", "mood_score", "interaction_freq", "deep_conversation"],
}


async def _dummy_checkin_handler(**kwargs):
    return {"status": "pending_checkin_flow", "data": kwargs}


register_tool(AgentTool(
    name="extract_checkin_data",
    description="当在聊天中收集到足够信息(心情、互动情况、发生的事件)时，提取这些数据用于生成当日关系日记。",
    parameters=extract_checkin_data_params,
    handler=_dummy_checkin_handler,
    needs_db=False,
    needs_pair_id=False,
))


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    pair_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession | None = None,
    allowed_names: set[str] | None = None,
    auth_cache: dict[tuple[str, str], User] | None = None,
) -> dict[str, Any]:
    """统一执行工具调用，并传入所需的数据库连接、关系编号和用户编号。

    auth_cache 为单次请求内的鉴权缓存：同一个 ReAct 循环中重复调用工具时，
    避免每次都重新加载用户并校验配对权限。
    """
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool or (allowed_names is not None and tool_name not in allowed_names):
        logger.warning(f"Tool not found: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    if not isinstance(arguments, dict):
        return {'status': 'error', 'message': '工具参数必须是对象'}
    kwargs = {key: value for key, value in arguments.items() if key in tool.parameters.get('properties', {})}
    if tool.needs_db:
        if db is None:
            return {"error": f"Tool {tool_name} requires a database session but none was provided."}
        kwargs["db"] = db
    if tool.needs_pair_id:
        if pair_id is None:
            return {"error": f"Tool {tool_name} requires pair_id but none was provided."}
        kwargs["pair_id"] = _normalize_uuid_param(pair_id)
    if tool.needs_user_id:
        if user_id is None:
            return {"error": f"Tool {tool_name} requires user_id but none was provided."}
        kwargs["user_id"] = _normalize_uuid_param(user_id)

    try:
        if tool.needs_db and tool.needs_pair_id:
            cache_key = (str(pair_id), str(user_id))
            actor = auth_cache.get(cache_key) if auth_cache is not None else None
            if actor is None:
                actor = await db.get(User, _normalize_uuid_param(user_id)) if user_id else None
                if actor is None:
                    return {'status': 'error', 'message': '请先登录'}
                await validate_pair_access(pair_id, actor, db, require_active=True)
                if auth_cache is not None:
                    auth_cache[cache_key] = actor
            kwargs['user_id'] = actor.id
        result = tool.handler(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return {"status": "success", "data": result}
    except Exception as e:
        logger.exception(f"Error executing tool {tool_name}")
        return {"status": "error", "message": "未能读取或处理这项信息，请检查权限和参数后重试"}


AGENT_TOOL_GUIDANCE = (
    "你可以调用以下工具来完成任务："
    + "、".join(f"「{name}」" for name in TOOL_REGISTRY)
    + "。请只在确有必要时调用工具，并基于返回结果组织回答。"
)


def get_openai_tools_schema(
    include_checkin: bool = True,
    allowed_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """生成工具定义。None 使用完整集合；空列表禁用全部工具。"""
    allow = set(allowed_names) if allowed_names is not None else None
    tools = []
    for tool in TOOL_REGISTRY.values():
        if tool.name == "extract_checkin_data" and not include_checkin:
            continue
        if allow is not None and tool.name not in allow:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        })
    return tools

"""Agent 工具注册表 — 将现有服务层包装为 Function Calling 工具

统一约定：handler 的签名尽量为 `(db, *, pair_id, user_id, **args)`，
由 execute_tool 注入 db / pair_id / user_id，args 来自模型的 tool_calls 参数。
"""

import asyncio
import logging
import re
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
    text = str(getattr(level, "value", level) or "").rsplit(".", 1)[-1].upper()
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

async def _get_relationship_status(db, *, pair_id=None, user_id=None, **kwargs):
    """当前关系的全景安全/健康状态。"""
    # build_safety_status 只认一个范围：有配对就看配对，没有才看个人。
    if pair_id:
        snapshot = await build_safety_status(db=db, pair_id=pair_id)
    elif user_id:
        snapshot = await build_safety_status(db=db, user_id=user_id)
    else:
        return {'status': 'ok', 'detail': '还没有可用的关系范围，暂时看不到安全状态。'}
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
    """主动检索跨会话的长期关系记忆；模型只拿到绑定具体记录内容的引用。"""
    from app.services.relationship_memory import memory_references, recall_memories
    types = [str(memory_type)] if memory_type else None
    rows = await recall_memories(
        db=db,
        pair_id=pair_id,
        user_id=user_id,
        query=str(query or ""),
        memory_types=types,
        limit=int(limit or 5),
    )
    ref_of = {item['record_id']: item['ref'] for item in await memory_references(db=db, pair_id=pair_id, user_id=user_id)}
    results = []
    for row in rows:
        content = row.get('content') or {}
        ref = ref_of.get(str(row.get('id')))
        entry = {
            'ref': ref,
            'type': row.get('type'),
            'subject': row.get('subject'),
            'detail': content.get('detail', ''),
            'importance': row.get('importance'),
            'remembered': content.get('memory_scope') or 'long_term',
        }
        if content.get('time_hint'):
            entry['time_hint'] = content['time_hint']
        evidence = content.get('person_evidence') or []
        if evidence:
            entry['person_evidence'] = [
                {'ref': f'{ref}-{index}', 'detail': item.get('detail', '')}
                for index, item in enumerate(evidence, 1)
            ]
        results.append(entry)
    if kwargs.get('current_message_id'):
        from app.services.chat_memory_permission import _verified_current_message
        from app.services.relationship_memory import fact_evidence
        verified = await _verified_current_message(db, session_id=kwargs.get('current_session_id'),
            user_message_id=kwargs['current_message_id'], user_id=user_id, pair_id=pair_id)
        if verified:
            message = verified[1]
            source_ids = set((message.payload or {}).get('memory_recall_source_ids') or [])
            for row in rows:
                content = row.get('content') or {}
                for evidence in [content, *fact_evidence(content), *(content.get('person_evidence') or [])]:
                    source_ids.update(str(evidence[field]) for field in ('source_user_message_id', 'authorization_user_message_id') if evidence.get(field))
            message.payload = {**(message.payload or {}), 'memory_recall_source_ids': sorted(source_ids)}
            await db.flush()
    return results


register_tool(AgentTool(
    name="recall_relationship_memories",
    description="主动检索跨会话的长期关系记忆（包括人物档案、过往冲突/事件、曾用沟通策略、相处模式与用户雷区底线）。当用户提起某人、过去某件事、需要参考历史经验或避免触碰禁忌时调用。person_evidence 是分别保存的原文，同一姓名下的不同明确身份要分别回答，不代表已经记混。用户只查询时不要主动拆分、重写或删除记忆，不要把内部记录形式当成需要用户处理的问题。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如人名、事件名、雷区或主题"},
            "memory_type": {"type": "string", "enum": ["person", "event", "strategy", "pattern", "taboo"], "description": "记忆类型：person(人物档案), event(重要事件), strategy(曾用策略), pattern(相处模式), taboo(用户雷区/忌讳/底线)"},
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
    from app.ai.skill_orchestrator import _COERCION_BLOCK_REASON, has_coercion_pressure

    result = build_message_preview_baseline(draft_text or "")
    if isinstance(result, dict) and has_coercion_pressure(draft_text):
        result = {
            **result,
            "risk_level": "high",
            "safer_rewrite": "",
            "rewrite_blocked": True,
            "rewrite_block_reason": _COERCION_BLOCK_REASON,
        }
    return result


async def _evaluate_intervention_need(db, *, pair_id=None, user_id=None, **kwargs):
    # 这个评估只按一个范围算：有配对就用配对，没配对就用个人，两个一起传会直接报错。
    if pair_id:
        evaluation = await build_intervention_evaluation(db=db, pair_id=pair_id)
    elif user_id:
        evaluation = await build_intervention_evaluation(db=db, user_id=user_id)
    else:
        return {"needed": False, "urgency": "monitor", "recommendation": "", "reason": "没有可评估的范围"}
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
    """按用户本轮意愿调用结构化分析；单人未绑定场景仅使用本轮原话与本人公开偏好，不读取其他配对资料。"""
    from app.ai.skill_orchestrator import analyze_for_chat, orchestrate
    from app.core.config import settings
    from app.models import Pair
    from app.services.companion_style import (
        build_simulation_style_context,
        merge_taboos,
        resolve_companion_context,
    )
    from app.services.relationship_memory import get_active_taboos, recall_memories

    memories = []
    pair_taboos = []
    pair_obj = None
    user_obj = None
    if db is not None and user_id is not None:
        try:
            user_obj = await db.get(User, _normalize_uuid_param(user_id))
        except Exception:
            user_obj = None
    if db is not None and pair_id is not None and user_id is not None:
        try:
            pair_obj = await db.get(Pair, _normalize_uuid_param(pair_id))
        except Exception:
            pair_obj = None
        try:
            memories = await recall_memories(
                db, pair_id=pair_id, user_id=user_id, query=str(complex_event_text or ""), limit=5,
            )
        except Exception:
            memories = []
        try:
            pair_taboos = await get_active_taboos(db, pair_id=pair_id, user_id=user_id)
        except Exception:
            pair_taboos = []

    companion_ctx = resolve_companion_context(
        user_obj,
        pair=pair_obj,
        pair_id=pair_id,
        current_text=str(complex_event_text or ""),
    )
    taboos = merge_taboos(companion_ctx.get("habit_taboos"), pair_taboos)
    style_context = build_simulation_style_context(companion_ctx, pair_taboos=pair_taboos)

    if settings.AI_CHAT_COMPACT_ANALYSIS:
        return await analyze_for_chat(
            str(complex_event_text or ""),
            intent=str(intent) if intent else None,
            memories=memories,
            taboos=taboos,
            style_context=style_context,
        )

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
    description=(
        "按用户本轮真实意愿调用，不按消息字数触发；单人未绑定伴侣也可使用。"
        "当用户明确希望梳理事情脉络、比较不同选择的取舍、规划下一步或复盘一次互动时调用"
        "（即便只有十几字，例如“现在说还是临近说，帮我比比”）。"
        "如果用户只是想吐槽倾诉、明确说“先别给建议/我就想说说”，或只需代写一句简短回复"
        "（如“帮我回一句今晚先不聊了”），不要调用本工具。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "complex_event_text": {"type": "string", "description": "用户描述的关系事件、纠结选项或待梳理原文"},
            "intent": {
                "type": "string",
                "enum": ["listen", "clarify", "resolve", "plan", "review"],
                "description": "本轮诉求：求理清用 clarify，求比较或要方案用 plan/resolve，求复盘用 review",
            },
        },
        "required": ["complex_event_text"],
    },
    handler=_run_skill_analysis,
    needs_db=True,
    needs_pair_id=False,
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
    description="提出一个待用户确认的行动建议，不会保存任务。单人也可以给本人提出安排。说明日期，只有用户点击加入安排后才保存；不要声称已安排。",
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
    needs_pair_id=False,
    needs_user_id=True,
))


_HABIT_CLAIM = re.compile(r'(每周|每天晚上|每天|每晚|一贯|总是|一直|长期|习惯|每次)')
# 检索返回的记录编号：R 加 16 个 A-P 字母，可选 -N 指向其中一份人物原文。
REF_PATTERN = re.compile(r'R[A-P]{16}(?:-[1-9][0-9]*)?')
# 用户自己的忌口、底线、不想被提的事，必须是 taboo 才会在下次对话里生效；
# 模型常把它当 person 存，这里兜一层。
_TABOO_HINT = re.compile(
    r'(忌口|不吃|不能吃|吃不了|受不了|讨厌|反感|吃不惯|别提|别问|不想提|不想听'
    r'|不许提|别再提|底线|雷区|忌讳|不能碰)'
)


_TIME_WORDS = re.compile(
    r'(大后天|后天|明天|今天|今晚|明早|明晚|昨天|前天'
    r'|(?:这|本|下个?)?周[一二三四五六日天]|(?:这|本|下个?)?星期[一二三四五六日天]'
    r'|\d{1,2}月\d{1,2}[日号]|\d{1,2}[日号])'
)


def _strip_time_words(text: str) -> str:
    """去掉主题里的时间词，只留"做什么/关于谁"，用来判断两条记录是不是同一件事。"""
    return re.sub(r'\s+', '', _TIME_WORDS.sub('', str(text or ''))).strip()


_CONFIRM_ONLY = re.compile(

    r'^[\s，。.!！?？]*(?:嗯+|好+|行+|可以|对|对呀|是的|要|记吧|记上|记下|记一下|记下来|记呗|那就记|那就记下|'
    r'麻烦记|请记|好啊|ok|OK|OK的|没问题|记住了)[\s，。.!！?？]*$'
)

# 只表达"记一下"这个动作、本身没有内容的词，剥掉这些字之后还剩字，才算说了新东西。
_FILLER = re.compile(
    r'[\s，。,.!！?？~—…、:：]|(?:这些|那些|这个|那个|这条|那条|这几条|上面|刚才|都|也|一并|一起|全部|'
    r'就|再|麻烦|请|帮我|给我|你|我|们|他|她|它|吧|了|呀|啊|哦|呗|哈|嗯|好|行|可以|没问题|对|是的|'
    r'记一下|记下来|记下来吧|记着|记住|记好|记上|记呗|记吧|记下|记事|记得|'
    r'存一下|存下来|存起来|保存|存|留个记录|留个底|再说一遍|说一遍)'
)


# 说过"这条不用记"的原话，只有在找不到别的依据时才拿来用。
_NO_NEED = re.compile(r'(?:不用|不要|不必|不需要|别)(?:再)?(?:记|存|留)')


def _has_substance(text: str | None) -> bool:
    """这句话里有没有实际内容，而不只是"记着""这些也记一下"这种动作。"""
    return len(_FILLER.sub('', str(text or ''))) >= 4


async def _grounding_evidence(db, *, session_id, current_message_id, evidence, detail=None) -> tuple[str, str | None]:
    """确认轮里用户只回一句"记吧"，真正的内容在上一轮；回溯取那条原话当依据。

    返回（作为依据的原话，原话所在的用户消息编号）。
    """
    from app.services.relationship_memory import _bigrams

    text = str(evidence or '').strip()
    summary = str(detail or '').strip()
    needs_backfill = not _has_substance(text)
    if re.fullmatch(r'(?:算了|想了想)?(?:还是)?(?:记一下|记下来|记着|记住|记吧|记上)[吧呗]?[,，]?(?:我(?:总是|总|老是)?忘(?:记)?)?', text.strip('。！!')):
        needs_backfill = True
    if re.search(r'(?:这|那)(?:两边|几个|几个人|些|个|几条).{0,6}(?:情况|说法|事|资料)?', text) and len(text)<=24:
        needs_backfill = True
    if not needs_backfill:
        return text, None
    if not db or not session_id:
        return text, None
    from sqlalchemy import select as _select
    from app.models import AgentChatMessage
    try:
        rows = (
            await db.execute(
                _select(AgentChatMessage)
                .where(AgentChatMessage.session_id == _normalize_uuid_param(session_id), AgentChatMessage.role == 'user')
                .order_by(AgentChatMessage.created_at.desc())
                .limit(12)
            )
        ).scalars().all()
    except Exception:
        return text, None
    fallback = None
    denied_fallback = None
    for row in rows:
        if (row.payload or {}).get('memory_suppressed_for_ai'):
            continue
        if current_message_id and str(row.id) == str(current_message_id):
            continue
        candidate = str(row.content or '').strip()
        if not _has_substance(candidate):
            continue
        if _NO_NEED.search(candidate):
            if denied_fallback is None:
                denied_fallback = (candidate, str(row.id))
            continue
        if not summary or len(_bigrams(candidate) & _bigrams(summary)) >= 2:
            return candidate, str(row.id)
        if fallback is None:
            fallback = (candidate, str(row.id))
    return fallback or denied_fallback or (text, None)


def _grounded_detail(detail, evidence) -> str:
    """摘要必须能在原话里找到依据；对不上就退回用户原话，不让模型补出新事实。"""
    from app.services.memory_evidence import grounded_summary
    return grounded_summary(detail, evidence)


async def _save_relationship_memory(db, *, pair_id, user_id=None, memory_type="event", subject="", content="", importance=3, **kwargs):
    """向跨会话长期关系知识库写入一条新记忆。原文和提炼出来的摘要分开存。"""
    from app.services.relationship_memory import store_memory
    evidence = str(kwargs.get('evidence_text') or '').strip()
    evidence, evidence_message_id = await _grounding_evidence(
        db,
        session_id=kwargs.get('current_session_id'),
        current_message_id=kwargs.get('current_message_id'),
        evidence=evidence,
        detail=content,
    )
    scope = str(kwargs.get('memory_scope') or 'long_term')
    hint = str(kwargs.get('time_hint') or '').strip()
    from app.services.memory_evidence import authorized_fact_text, grounded_subject, topic_without_time, candidate_matches_source
    evidence = authorized_fact_text(evidence)
    if not evidence_message_id and not candidate_matches_source(subject, content, evidence, memory_type):
        return {'status':'error','saved':False,'message':'这项提炼不对应本轮授权原话，未保存。请只提交本轮要求的主题和原文，不要补存其他话题。'}
    subject = grounded_subject(subject, evidence, memory_type)
    detail = _grounded_detail(content, evidence)
    memory_type = str(memory_type or 'event').strip().lower()
    importance = int(importance or 3)
    correction_target = None
    if scope == 'correction':
        from app.models import RelationshipMemory
        target_id = _normalize_uuid_param(kwargs.get('correction_memory_id'))
        correction_target = await db.get(RelationshipMemory,target_id) if isinstance(target_id,uuid.UUID) else None
        if correction_target is None or correction_target.user_id!=_normalize_uuid_param(user_id) or correction_target.pair_id!=_normalize_uuid_param(pair_id):
            return {'status':'confirmation_required','saved':False,'message':'没有确认要修改哪条已保存记录，未新增或修改记忆。'}
        subject = topic_without_time(correction_target.subject) or correction_target.subject
        memory_type = correction_target.memory_type
        scope = 'dated' if hint or (correction_target.content or {}).get('memory_scope')=='dated' else 'long_term'
    if scope == 'dated':
        # 一次性的安排只记这一次的事，不能升格成长期习惯或雷区。
        memory_type = 'event'
        importance = min(importance, 3)
        if _HABIT_CLAIM.search(detail):
            detail = evidence or detail
        if hint and hint not in subject:
            subject = (subject + f'（{hint}）')[:100]
        if hint and hint not in detail:
            detail = f'{detail}；时间限定：{hint}'
    elif _TABOO_HINT.search(f'{subject} {detail} {evidence}'):
        # 忌口和底线要进 taboo，否则下次对话不会作为约束加载。
        memory_type = 'taboo'
        importance = max(importance, 4)
    payload = {
        'detail': detail,
        'evidence_text': evidence or detail,
        'memory_scope': scope,
        'source_user_message_id': str(evidence_message_id or kwargs.get('source_user_message_id') or ''),
        'authorization_user_message_id': str(kwargs.get('current_message_id') or kwargs.get('source_user_message_id') or ''),
    }
    if hint:
        payload['time_hint'] = hint
    if correction_target is not None:
        # 更新已经核对的那条，保留记录身份；旧引用会因内容变更自动失效。
        from app.services.relationship_memory import fact_evidence
        previous_content = correction_target.content or {}
        previous_sources = set(previous_content.get('retired_source_ids') or [])
        for entry in [previous_content, *fact_evidence(previous_content), *(previous_content.get('person_evidence') or [])]:
            previous_sources.update(str(entry[field]) for field in ('source_user_message_id', 'authorization_user_message_id') if entry.get(field))
        payload['retired_source_ids'] = sorted(previous_sources)
        correction_target.subject = subject[:100]
        correction_target.memory_type = memory_type
        correction_target.importance = importance
        correction_target.content = dict(payload)
        if memory_type=='person':
            correction_target.content = {**payload,'person_evidence':[{'detail':detail,'source_user_message_id':payload['source_user_message_id']}]}
        correction_target.source_session_id = _normalize_uuid_param(kwargs.get('source_session_id'))
        await db.flush()
        mem = correction_target
    else:
        mem = await store_memory(
            db, pair_id=pair_id, user_id=user_id, memory_type=memory_type,
            subject=subject, content=payload, importance=importance,
            source_session_id=kwargs.get('source_session_id'),
        )
    return {
        "status": "success",
        "memory_id": str(mem.id),
        "subject": mem.subject,
        "memory_type": mem.memory_type,
        "importance": mem.importance,
        "remembered": scope,
    }


register_tool(AgentTool(
    name="save_relationship_memory",
    description="保存用户明确要求记住的内容，包括稳定情况和带日期的一次安排。用户说“记一下”“你得记着”已是保存要求，先调用工具；日期安排按原话只记这一次，不必先追问是不是每周。只是顺口提到安排、心情或稳定情况但没要求记时，不主动存；用户说不用记就别存。没确认保存意愿时才问一句。忌口和底线用 taboo；不得补出每周习惯，不得借本轮授权补存别的话题；以工具返回为准，不得虚报成功。",
    parameters={
        "type": "object",
        "properties": {
            "memory_type": {"type": "string", "enum": ["person", "event", "strategy", "pattern", "taboo"], "description": "记忆类型：person(人物档案), event(重要事件), strategy(曾用策略), pattern(相处模式), taboo(用户雷区/忌讳/底线/试过无效的做法)"},
            "subject": {"type": "string", "description": "记忆主题、雷区关键词或人名（简明精准，10字以内）"},
            "content": {"type": "string", "description": "详细内容、共识、用户明确反感的事项或试过没用的做法"},
            "importance": {"type": "integer", "description": "重要度 1-5（雷区底线通常为 4 或 5，普通事件默认为 3）", "default": 3},
        },
        "required": ["subject", "content"],
    },
    handler=_save_relationship_memory,
    needs_db=True,
    needs_pair_id=True,
    needs_user_id=True,
    category="action",
))


async def _remove_relationship_memory(db, *, pair_id, user_id=None, subject="", memory_type=None, refs=None, person_selector=None, memory_id=None, evidence_ids=None, delete_all=False, request_text=None, all_scope_requested=False, session_id=None, user_message_id=None, **kwargs):
    """只提出停用范围，用户二次确认前不改记忆。"""
    from app.services.memory_removal import prepare_removal
    try:
        return await prepare_removal(db,session_id=session_id,user_message_id=user_message_id,user_id=user_id,pair_id=pair_id,
            subject=subject,memory_type=memory_type,refs=refs,person_selector=person_selector,memory_id=memory_id,
            evidence_ids=evidence_ids,delete_all=delete_all,request_text=request_text,all_scope_requested=all_scope_requested)
    except ValueError as error:
        return {'status':'clarification_required','removed':False,'message':str(error)}


register_tool(AgentTool(
    name="remove_relationship_memory",
    description="按用户本轮要求提出记忆停用范围，必须二次确认；本工具不会立即删除。用户说不用记了、删了吧时先调用本工具展示范围与保留说明，不能声称已经完成。只有用户看到提示后另发确认，服务端才会执行。同名人物按本轮明确身份填写 person_selector；已给姓名和身份时优先只传 subject 与 person_selector，不额外生成 refs。如需引用，只能原样使用实际检索返回的 ref。未说清楚先问。模型不能代替用户确认，也不提供确认执行参数。",
    parameters={
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "要删除的记忆主题或雷区关键词，尽量用用户本轮的原话"},
            "memory_type": {"type": "string", "enum": ["person", "event", "strategy", "pattern", "taboo"], "description": "记忆类型"},
            "refs": {"type": "array", "items": {"type": "string"}, "description": "原样使用检索返回的完整 ref；它绑定具体记录及内容，不能编造序号，记录修改后须重新检索"},
            "person_selector": {"type":"string","description":"用户本轮原话明确提供的身份，例如球友、公司同事；不能只填同名姓名"},
            "delete_all": {"type":"boolean","description":"仅当用户明确要求删除整个主题全部资料时使用","default":False},
        },
    },
    handler=_remove_relationship_memory,
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
    session_id: str | None = None,
    user_message_id: str | None = None,
    db: AsyncSession | None = None,
    allowed_names: set[str] | None = None,
    auth_cache: dict[tuple[str, str], User] | None = None,
    extra: dict[str, Any] | None = None,
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
    if extra:
        # 服务端自己核对出来的上下文（例如“刚才那条”指的是上一轮存下的那条），不需要模型填。
        kwargs.update(extra)
    if tool.needs_db:
        if db is None:
            return {"error": f"Tool {tool_name} requires a database session but none was provided."}
        kwargs["db"] = db
    if tool.needs_pair_id:
        if pair_id is None:
            return {"error": f"Tool {tool_name} requires pair_id but none was provided."}
        kwargs["pair_id"] = _normalize_uuid_param(pair_id)
    elif tool_name in {"run_skill_analysis", "create_task"}:
        kwargs["pair_id"] = _normalize_uuid_param(pair_id) if pair_id is not None else None
    if tool.needs_user_id:
        if user_id is None:
            return {"error": f"Tool {tool_name} requires user_id but none was provided."}
        kwargs["user_id"] = _normalize_uuid_param(user_id)

    try:
        requires_pair_validation = tool.needs_db and (
            tool.needs_pair_id or (tool_name in {"run_skill_analysis", "create_task"} and pair_id is not None)
        )
        if requires_pair_validation:
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
        elif tool.needs_db and tool_name in {"run_skill_analysis", "create_task"} and user_id is not None:
            actor = await db.get(User, _normalize_uuid_param(user_id))
            if actor is None:
                return {'status': 'error', 'message': '请先登录'}
            kwargs['user_id'] = actor.id
        if tool_name == 'recall_relationship_memories':
            kwargs['current_session_id'] = session_id
            kwargs['current_message_id'] = user_message_id
        if tool_name == 'save_relationship_memory':
            from app.services.chat_memory_permission import verified_memory_request
            kwargs['current_session_id'] = session_id
            kwargs['current_message_id'] = user_message_id
            grant = await verified_memory_request(db, session_id=session_id, user_message_id=user_message_id, user_id=user_id, pair_id=pair_id)
            if grant is None:
                return {'status': 'confirmation_required', 'data': {'status': 'confirmation_required', 'saved': False}, 'message': '还没保存。这句不是明确的保存要求，先用一句话问用户要不要长期记下来。'}
            kwargs.update(grant)
        if tool_name == 'remove_relationship_memory':
            from app.services.chat_memory_permission import verified_memory_removal
            grant = await verified_memory_removal(db, session_id=session_id, user_message_id=user_message_id, user_id=user_id, pair_id=pair_id)
            if grant is None:
                return {'status': 'clarification_required', 'data': {'status': 'clarification_required', 'removed': False}, 'message': '还没删。这句不是在要求删除，先问一句要不要删。'}
            selector = str(kwargs.get('person_selector') or '').strip()
            if selector and selector not in grant['request_text']:
                return {'status':'error','message':'未删除。人物身份必须来自用户本轮原话，请先确认是哪位。'}
            kwargs['session_id'] = session_id
            kwargs['user_message_id'] = user_message_id
            # “刚才那条不用记了”由服务端按上一轮消息定位，原话里没有内容可对，跳过原话比对。
            kwargs['request_text'] = None if kwargs.get('deictic') else grant['request_text']
            kwargs['all_scope_requested'] = grant.get('all_scope_requested',False)
            kwargs['delete_all'] = bool(kwargs.get('delete_all') and grant['all_requested'])
            refs = kwargs.get('refs')
            if refs is not None:
                if not isinstance(refs, list) or any(not REF_PATTERN.fullmatch(str(item).strip()) for item in refs):
                    return {'status':'clarification_required','data':{'status':'clarification_required','removed':False},'message':'还没删。记录编号对不上，请用检索结果里的 R 编号（例如 R2，人物原文再加 -1）重新说一次。'}
        result = tool.handler(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        if isinstance(result, dict) and result.get('status') in ('clarification_required', 'confirmation_required', 'not_found', 'error'):
            return {'status': result['status'], 'data': result, 'message': result.get('message', '')}
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
    pair_available: bool = True,
) -> list[dict[str, Any]]:
    """生成工具定义。None 使用完整集合；空列表禁用全部工具。"""
    allow = set(allowed_names) if allowed_names is not None else None
    tools = []
    for tool in TOOL_REGISTRY.values():
        if tool.needs_pair_id and not pair_available:
            continue
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

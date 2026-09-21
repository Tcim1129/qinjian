"""分析结果的数据格式：将各模块的输出整理后交给前端显示。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.skill_registry import SkillOutput
    from app.ai.skill_orchestrator import OrchestrationPlan


@dataclass
class SkillStep:
    """Skill 执行步骤的记录（供前端展示执行轨迹）。"""
    skill_name: str
    skill_label: str
    status: str = "ok"       # ok / error / skipped
    duration_ms: float = 0.0
    reason: str | None = None


@dataclass
class ProblemSummary:
    """问题摘要卡。"""
    people: list[dict[str, str]] = field(default_factory=list)
    events: list[dict[str, str]] = field(default_factory=list)
    user_emotion: str = ""
    core_need: str = ""
    priority_issue: str = ""


@dataclass
class StanceCard:
    """立场卡片。"""
    person: str = ""
    position: str = ""
    underlying_need: str = ""
    worry: str = ""
    flexibility: str = "medium"


@dataclass
class ActionProposal:
    """行动方案。"""
    id: str = "A"
    title: str = ""
    description: str = ""
    approach: str = "gentle"
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    effort: str = "medium"
    recommended: bool = False


@dataclass
class CommunicationDraft:
    """沟通草稿。"""
    drafts: list[dict[str, str]] = field(default_factory=list)
    opening_line: str = ""
    tone_guide: str = ""
    avoid: list[str] = field(default_factory=list)
    best_channel: str = ""


@dataclass
class ReviewTask:
    """复盘任务。"""
    event_summary: str = ""
    what_worked: list[str] = field(default_factory=list)
    what_to_improve: list[str] = field(default_factory=list)
    lesson: str = ""
    pattern_noticed: str = ""
    next_attention: str = ""


@dataclass
class DeliveryPackage:
    """汇总各分析模块的结果和建议。"""
    # 核心交付内容
    summary: ProblemSummary = field(default_factory=ProblemSummary)
    stances: list[StanceCard] = field(default_factory=list)
    conflict: dict[str, Any] = field(default_factory=dict)
    proposals: list[ActionProposal] = field(default_factory=list)
    draft: CommunicationDraft | None = None
    review: ReviewTask | None = None

    # 元信息
    primary_intent: str = "resolve"
    is_complex: bool = True
    skill_trace: list[SkillStep] = field(default_factory=list)
    total_duration_ms: float = 0.0

    # 长期记忆提取
    memories_to_save: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        result: dict[str, Any] = {
            "summary": {
                "people": self.summary.people,
                "events": self.summary.events,
                "user_emotion": self.summary.user_emotion,
                "core_need": self.summary.core_need,
                "priority_issue": self.summary.priority_issue,
            },
            "stances": [
                {
                    "person": s.person,
                    "position": s.position,
                    "underlying_need": s.underlying_need,
                    "worry": s.worry,
                    "flexibility": s.flexibility,
                }
                for s in self.stances
            ],
            "conflict": self.conflict,
            "proposals": [
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "approach": p.approach,
                    "pros": p.pros,
                    "cons": p.cons,
                    "effort": p.effort,
                    "recommended": p.recommended,
                }
                for p in self.proposals
            ],
            "draft": None,
            "review": None,
            "primary_intent": self.primary_intent,
            "is_complex": self.is_complex,
            "skill_trace": [
                {
                    "skill_name": s.skill_name,
                    "skill_label": s.skill_label,
                    "status": s.status,
                    "duration_ms": round(s.duration_ms, 1),
                    "reason": s.reason,
                }
                for s in self.skill_trace
            ],
            "total_duration_ms": round(self.total_duration_ms, 1),
            "memories_to_save": self.memories_to_save,
        }

        if self.draft:
            result["draft"] = {
                "drafts": self.draft.drafts,
                "opening_line": self.draft.opening_line,
                "tone_guide": self.draft.tone_guide,
                "avoid": self.draft.avoid,
                "best_channel": self.draft.best_channel,
            }

        if self.review:
            result["review"] = {
                "event_summary": self.review.event_summary,
                "what_worked": self.review.what_worked,
                "what_to_improve": self.review.what_to_improve,
                "lesson": self.review.lesson,
                "pattern_noticed": self.review.pattern_noticed,
                "next_attention": self.review.next_attention,
            }

        return result


def _safe_list(data: dict, key: str) -> list:
    value = data.get(key)
    return value if isinstance(value, list) else []


def _safe_str(data: dict, key: str, default: str = "") -> str:
    value = data.get(key)
    return str(value).strip() if value else default


def assemble_delivery_package(
    *,
    results: dict[str, "SkillOutput"],
    skill_steps: list[SkillStep],
    plan: "OrchestrationPlan",
    total_duration_ms: float,
) -> DeliveryPackage:
    """将各分析模块的输出整理为统一的结果。"""
    package = DeliveryPackage(
        primary_intent=plan.primary_intent,
        is_complex=plan.is_complex,
        skill_trace=skill_steps,
        total_duration_ms=total_duration_ms,
    )

    # 表达澄清 → 问题摘要
    clarify = results.get("expression_clarify")
    if clarify and clarify.success:
        data = clarify.data
        package.summary = ProblemSummary(
            people=_safe_list(data, "people"),
            events=_safe_list(data, "events"),
            user_emotion=_safe_str(data, "user_emotion"),
            core_need=_safe_str(data, "core_need"),
        )

    # 立场分析 → 立场卡片
    stance = results.get("stance_analysis")
    if stance and stance.success:
        data = stance.data
        for item in _safe_list(data, "stances"):
            if isinstance(item, dict):
                package.stances.append(StanceCard(
                    person=_safe_str(item, "person"),
                    position=_safe_str(item, "position"),
                    underlying_need=_safe_str(item, "underlying_need"),
                    worry=_safe_str(item, "worry"),
                    flexibility=_safe_str(item, "flexibility", "medium"),
                ))

    # 冲突识别
    conflict = results.get("conflict_detect")
    if conflict and conflict.success:
        package.conflict = conflict.data
        package.summary.priority_issue = _safe_str(
            conflict.data, "priority_issue",
        )

    # 行动规划 → 方案
    action = results.get("action_plan")
    if action and action.success:
        data = action.data
        for item in _safe_list(data, "proposals"):
            if isinstance(item, dict):
                package.proposals.append(ActionProposal(
                    id=_safe_str(item, "id", "A"),
                    title=_safe_str(item, "title"),
                    description=_safe_str(item, "description"),
                    approach=_safe_str(item, "approach", "gentle"),
                    pros=_safe_list(item, "pros"),
                    cons=_safe_list(item, "cons"),
                    effort=_safe_str(item, "effort", "medium"),
                    recommended=bool(item.get("recommended")),
                ))

    # 沟通草稿
    draft = results.get("draft_message")
    if draft and draft.success:
        data = draft.data
        package.draft = CommunicationDraft(
            drafts=_safe_list(data, "drafts"),
            opening_line=_safe_str(data, "opening_line"),
            tone_guide=_safe_str(data, "tone_guide"),
            avoid=_safe_list(data, "avoid"),
            best_channel=_safe_str(data, "best_channel"),
        )

    # 复盘
    review = results.get("review")
    if review and review.success:
        data = review.data
        package.review = ReviewTask(
            event_summary=_safe_str(data, "event_summary"),
            what_worked=_safe_list(data, "what_worked"),
            what_to_improve=_safe_list(data, "what_to_improve"),
            lesson=_safe_str(data, "lesson"),
            pattern_noticed=_safe_str(data, "pattern_noticed"),
            next_attention=_safe_str(data, "next_attention"),
        )

    # 关系记忆提取
    memory = results.get("memory_write")
    if memory and memory.success:
        package.memories_to_save = _safe_list(memory.data, "memories")

    return package

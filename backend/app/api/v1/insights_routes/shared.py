"""Shared helpers for relationship insight routes."""

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import validate_pair_access
from app.models import (
    Checkin,
    InterventionPlan,
    Pair,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    User,
)
from app.services.relationship_intelligence import refresh_profile_snapshot
from app.services.checkin_visibility import PARTNER_VISIBLE_SCOPES
from app.services.display_labels import (
    DECISION_FEEDBACK_LABELS,
    decision_feedback_label,
    plan_type_label,
    report_type_label,
    risk_level_label,
    status_label,
    task_category_label,
    translate_inline_codes,
)


async def resolve_scope(
    *,
    pair_id: str | None,
    mode: str | None,
    user: User,
    db: AsyncSession,
) -> tuple[str | None, str | None]:
    if mode == "solo":
        return None, str(user.id)

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=False)
    return pair_id, None


def _scope_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def profile_scope_query(pair_id: str | None, user_id: str | None):
    pair_uuid = _scope_uuid(pair_id)
    user_uuid = _scope_uuid(user_id)
    if pair_id:
        return [
            RelationshipProfileSnapshot.pair_id == pair_uuid,
            RelationshipProfileSnapshot.user_id.is_(None),
        ]
    return [
        RelationshipProfileSnapshot.user_id == user_uuid,
        RelationshipProfileSnapshot.pair_id.is_(None),
    ]


def plan_scope_query(pair_id: str | None, user_id: str | None):
    pair_uuid = _scope_uuid(pair_id)
    user_uuid = _scope_uuid(user_id)
    if pair_id:
        return [
            InterventionPlan.pair_id == pair_uuid,
            InterventionPlan.user_id.is_(None),
        ]
    return [
        InterventionPlan.user_id == user_uuid,
        InterventionPlan.pair_id.is_(None),
    ]


def event_scope_query(pair_id: str | None, user_id: str | None):
    pair_uuid = _scope_uuid(pair_id)
    user_uuid = _scope_uuid(user_id)
    if pair_id:
        return [RelationshipEvent.pair_id == pair_uuid]
    return [
        RelationshipEvent.user_id == user_uuid,
        RelationshipEvent.pair_id.is_(None),
    ]


def dedupe_theory_cards(cards: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        key = str(card.get("id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(card)
    return deduped


def repair_protocol_type_for_level(level: str) -> str:
    if level == "severe":
        return "de_escalation_protocol"
    if level == "moderate":
        return "structured_repair"
    if level == "mild":
        return "gentle_repair"
    return "steady_maintenance"


def timeline_category_for_event(event_type: str) -> str:
    if event_type.startswith("pair."):
        return "action"
    if event_type.startswith("client."):
        return "client"
    if event_type.startswith("privacy."):
        return "privacy"
    if event_type.startswith("checkin."):
        return "checkin"
    if event_type.startswith("report."):
        return "report"
    if event_type.startswith("crisis."):
        return "risk"
    if event_type.startswith("safety."):
        return "risk"
    if event_type.startswith("task."):
        return "action"
    if event_type.startswith("playbook."):
        return "playbook"
    if event_type.startswith("plan."):
        return "strategy"
    if event_type.startswith("message."):
        return "coach"
    if event_type.startswith("alignment."):
        return "alignment"
    if event_type.startswith("assessment."):
        return "assessment"
    return "system"


def timeline_category_label(category: str) -> str:
    return {
        "client": "端侧",
        "privacy": "隐私",
        "checkin": "记录",
        "report": "洞察",
        "risk": "风险",
        "action": "行动",
        "playbook": "剧本",
        "strategy": "策略",
        "coach": "教练",
        "alignment": "对齐",
        "assessment": "体检",
        "system": "系统",
    }.get(category, "系统")


def timeline_tone_for_event(event_type: str, payload: dict) -> str:
    if event_type in {"pair.join_approved", "pair.type_change_approved"}:
        return "progress"
    if event_type in {"pair.join_requested", "pair.type_change_requested"}:
        return "movement"
    if event_type in {"crisis.raised", "crisis.updated"}:
        return "warning"
    if event_type in {"client.risk.flagged", "safety.crisis_gate_opened"}:
        return "warning"
    if event_type in {"crisis.resolved", "task.completed", "task.feedback_submitted"}:
        return "progress"
    if event_type in {"report.completed", "plan.evaluation_snapshot"}:
        return "insight"
    if event_type in {"message.simulated", "alignment.generated"}:
        return "support"
    if event_type in {"playbook.transitioned", "task.generated"}:
        return "movement"
    if payload.get("risk_level") in {"moderate", "severe"}:
        return "warning"
    return "neutral"


def timeline_tone_label(tone: str) -> str:
    return {
        "warning": "需要留意",
        "progress": "正在推进",
        "insight": "得到洞察",
        "support": "辅助理解",
        "movement": "状态切换",
        "neutral": "持续记录",
    }.get(tone, "持续记录")


TIMELINE_INTENT_LABELS = {
    "daily": "日常记录",
    "reflection": "关系复盘",
    "conflict": "冲突梳理",
    "repair": "修复沟通",
    "plan": "行动安排",
    "wording": "表达调整",
    "emergency": "高风险求助",
    "crisis": "高风险求助",
}

TIMELINE_INTENSITY_LABELS = {
    "gentle": "轻节奏",
    "light": "轻节奏",
    "low": "轻节奏",
    "steady": "稳步推进",
    "medium": "适中节奏",
    "high": "加紧关注",
    "reduce_load": "先降负荷",
}

TIMELINE_BRANCH_LABELS = {
    "steady": "稳步推进",
    "reduce_load": "先降负荷",
    "deepen": "加深连接",
    "repair": "温和修复",
    "cooldown": "先降温",
}

TIMELINE_MOMENTUM_LABELS = {
    "improving": "走势向好",
    "steady": "保持平稳",
    "stable": "保持平稳",
    "declining": "需要留意",
    "worsening": "波动偏大",
}

TIMELINE_SUFFICIENCY_LABELS = {
    "sufficient": "样本充足",
    "limited": "样本积累中",
    "partial": "样本积累中",
    "insufficient": "样本较少",
}

TIMELINE_BASELINE_MATCH_LABELS = {
    "aligned": "接近平时状态",
    "deviation": "与平时有所不同",
    "shifted": "有明显变化",
}

TIMELINE_REACTION_SHIFT_LABELS = {
    "closer": "更愿靠近",
    "warmer": "态度缓和",
    "steady": "较平稳",
    "defensive": "偏防御",
    "withdrawn": "偏回避",
    "tense": "偏紧张",
    "escalated": "情绪偏紧",
}

TIMELINE_UPLOAD_POLICY_LABELS = {
    "full": "完整保存",
    "summary_only": "仅存摘要",
    "local_only": "仅存本地",
}

TIMELINE_SOURCE_LABELS = {
    "system": "系统记录",
    "user": "用户操作",
    "client": "客户端",
    "ai": "智能助手",
    "mobile": "移动端",
    "admin": "管理操作",
}

TIMELINE_TRANSITION_TYPE_LABELS = {
    "initialized": "开始执行",
    "advanced": "进入下一步",
    "branch_switched": "切换节奏",
    "completed": "阶段完成",
}

TIMELINE_TRIGGER_TYPE_LABELS = {
    "run_started": "方案启动",
    "checkin": "日常记录触发",
    "report": "简报更新触发",
    "task_feedback": "任务反馈触发",
    "risk_change": "状态变化触发",
    "manual": "手动调整",
}

TIMELINE_CRISIS_REASON_LABELS = {
    "level_changed": "预警等级已变化",
    "auto_recovered": "关系状态恢复平稳",
    "user_resolved": "已手动标记解除",
}


def timeline_source_label(source: str | None) -> str:
    return TIMELINE_SOURCE_LABELS.get(str(source or "").strip().lower(), "系统记录")


def timeline_branch_label(branch: str | None) -> str:
    key = str(branch or "").strip().lower()
    return TIMELINE_BRANCH_LABELS.get(key, translate_inline_codes(branch) or "当前阶段")


def timeline_transition_type_label(value: str | None) -> str:
    key = str(value or "").strip().lower()
    return TIMELINE_TRANSITION_TYPE_LABELS.get(key, "状态推进")


def timeline_trigger_type_label(value: str | None) -> str:
    key = str(value or "").strip().lower()
    return TIMELINE_TRIGGER_TYPE_LABELS.get(key, "系统触发")


def timeline_event_label(event_type: str) -> str:
    labels = {
        "pair.join_requested": "加入请求待确认",
        "pair.join_approved": "关系已确认建立",
        "pair.join_rejected": "加入请求未被确认",
        "pair.type_change_requested": "关系类型切换待确认",
        "pair.type_change_approved": "关系类型已切换",
        "pair.type_change_rejected": "关系类型切换未被确认",
        "pair.request_cancelled": "关系请求已撤回",
        "pair.break_requested": "发起了关系解除申请",
        "pair.break_retention_started": "关系进入挽留确认期",
        "pair.break_completed": "关系已解除",
        "client.precheck.completed": "记录前预检已完成",
        "client.risk.flagged": "发现了需要留意的信号",
        "privacy.ai.chat.logged": "记录了一次智能文本调用",
        "privacy.ai.transcription.logged": "记录了一次语音转写调用",
        "privacy.upload.created": "保存了一份私有上传文件",
        "privacy.upload.access_denied": "拦截了一次超出范围的文件访问",
        "privacy.status.viewed": "查看了隐私保护状态",
        "privacy.delete.requested": "发起了删除请求",
        "privacy.delete.cancelled": "撤回了删除请求",
        "privacy.delete.executed": "执行了隐私删除流程",
        "privacy.delete.manual_review": "删除请求进入人工复核",
        "privacy.delete.rejected": "删除请求被驳回",
        "privacy.retention.purged": "执行了一次隐私保留清扫",
        "privacy.benchmark.ran": "完成了一次文本隐私代理评测",
        "checkin.created": "完成了一次记录",
        "checkin.submit": "完成了一次记录",
        "checkin.precheck": "记录前预检已完成",
        "checkin.local_saved": "记录先保存在本地",
        "checkin.synced": "本地记录已同步到云端",
        "checkin.analyzed": "记录分析已更新",
        "report.completed": "新简报生成完成",
        "report.discarded": "简报已随分享撤回作废",
        "safety.crisis_gate_opened": "安全边界已被触发",
        "safety.status_viewed": "查看安全状态",
        "crisis.raised": "风险信号被抬升",
        "crisis.updated": "风险状态已刷新",
        "crisis.resolved": "风险信号已回落",
        "task.generated": "系统排出了新安排",
        "task.updated": "今日安排已更新",
        "task.refreshed": "今日安排已刷新",
        "task.reopened": "安排已重新打开",
        "task.importance_changed": "安排优先级已调整",
        "task.reminder_sent": "已发送安排提醒",
        "task.completed": "一项安排已完成",
        "task.feedback_submitted": "安排反馈已记录",
        "playbook.transitioned": "阶段节奏已调整",
        "message.simulated": "发前看看已完成",
        "coach.simulate_message": "发前看看已完成",
        "alignment.generated": "双视角对齐已生成",
        "insights.alignment.generated": "双视角对齐已生成",
        "message.feedback_submitted": "消息判断反馈已提交",
        "alignment.feedback_submitted": "双视角反馈已提交",
        "decision.feedback_submitted": "判断反馈已提交",
        "plan.evaluation_snapshot": "阶段效果评估已更新",
        "assessment.weekly_submitted": "完成了一次关系体检",
        "assessment.weekly_stable_band_detected": "关系体检分数保持稳定",
        "attachment.analyzed": "依恋倾向分析已更新",
        "agent.checkup.completed": "主动巡查已完成",
        "mobile.action.result": "更新了安排结果",
        "mobile.action.completed": "完成了一项安排",
        "mobile.action.feedback": "提交了安排反馈",
        "mobile.alignment.feedback": "提交了双视角反馈",
    }
    if event_type in labels:
        return labels[event_type]
    if event_type.endswith(".completed"):
        return "一个节点已完成"
    if event_type.endswith(".generated"):
        return "系统生成了新的整理"
    if event_type.endswith(".submitted"):
        return "已提交一条反馈"
    return "关系记录更新"


def format_timeline_summary(event: RelationshipEvent) -> tuple[str, str | None]:
    payload = event.payload or {}
    event_type = event.event_type

    if event_type == "client.precheck.completed":
        intent_key = str(payload.get("intent") or "daily").strip().lower()
        intent_label = TIMELINE_INTENT_LABELS.get(intent_key, "日常记录")
        risk_label = risk_level_label(payload.get("risk_level") or "none")
        tags = payload.get("client_tags") or []
        summary = f"完成了一次{intent_label}预检"
        detail = f"当前状态：{risk_label}"
        if tags:
            detail = f"{detail}，标签：{'，'.join(str(item) for item in tags[:3])}"
        return summary, detail

    if event_type == "pair.join_requested":
        requested_type = payload.get("requested_type_label") or "待确认关系"
        actor_name = payload.get("actor_nickname") or "对方"
        return (
            f"{actor_name} 提交了加入请求",
            f"希望按“{requested_type}”建立，等待另一方确认",
        )

    if event_type == "pair.join_approved":
        requested_type = payload.get("requested_type_label") or "当前关系"
        actor_name = payload.get("actor_nickname") or "对方"
        return (
            f"{actor_name} 确认了这次加入请求",
            f"这段关系现在按“{requested_type}”生效",
        )

    if event_type == "pair.join_rejected":
        actor_name = payload.get("actor_nickname") or "对方"
        return f"{actor_name} 暂未确认这次加入请求", "这次加入未生效，可以稍后重新发起"

    if event_type == "pair.type_change_requested":
        requested_type = payload.get("requested_type_label") or "新关系类型"
        actor_name = payload.get("actor_nickname") or "对方"
        previous_type = payload.get("previous_type_label")
        detail = f"希望切换成“{requested_type}”"
        if previous_type:
            detail = f"从“{previous_type}”切到“{requested_type}”"
        return f"{actor_name} 发起了关系类型切换", detail

    if event_type == "pair.type_change_approved":
        actor_name = payload.get("actor_nickname") or "对方"
        requested_type = payload.get("requested_type_label") or "新关系类型"
        return f"{actor_name} 确认了关系类型切换", f"系统之后会按“{requested_type}”处理这段关系"

    if event_type == "pair.type_change_rejected":
        actor_name = payload.get("actor_nickname") or "对方"
        return f"{actor_name} 暂未确认这次关系类型切换", "系统仍按原关系类型处理"

    if event_type == "pair.request_cancelled":
        actor_name = payload.get("actor_nickname") or "对方"
        kind_label = payload.get("request_kind_label") or "关系请求"
        return f"{actor_name} 撤回了这次{kind_label}", "这条待确认请求已经结束"

    if event_type == "client.risk.flagged":
        hits = payload.get("risk_hits") or []
        risk_text = risk_level_label(payload.get("risk_level") or "watch")
        summary = f"捕捉到{risk_text}风险信号"
        return summary, f"命中关键词：{'，'.join(str(item) for item in hits[:4])}" if hits else None

    if event_type == "privacy.ai.chat.logged":
        status = str(payload.get("status") or "").strip().lower()
        if status in {"error", "failed"}:
            error_code = payload.get("error_code")
            return (
                "记录了一次失败的智能文本调用",
                f"错误类型：{error_code}" if error_code else None,
            )
        return "记录了一次智能文本调用", None

    if event_type == "privacy.ai.transcription.logged":
        status = str(payload.get("status") or "").strip().lower()
        detail_parts: list[str] = []
        audio_info = payload.get("audio_info") or {}
        if audio_info.get("language_label"):
            detail_parts.append(f"语言：{audio_info.get('language_label')}")
        if payload.get("input_summary_redacted"):
            detail_parts.append(f"文件：{payload.get('input_summary_redacted')}")
        if status in {"error", "failed"} and payload.get("error_code"):
            detail_parts.insert(0, f"错误类型：{payload.get('error_code')}")
            return "记录了一次失败的语音转写调用", "，".join(detail_parts) if detail_parts else None
        return "记录了一次语音转写调用", "，".join(detail_parts) if detail_parts else None

    if event_type == "checkin.created":
        mode = "个人" if payload.get("mode") == "solo" else "关系"
        mood = payload.get("mood_score")
        summary = (
            f"{mode}记录已写入"
            f"{f'，情绪分 {mood}' if mood is not None else ''}"
        )
        detail_parts = []
        if payload.get("deep_conversation") is True:
            detail_parts.append("记录里提到有深聊")
        if payload.get("task_completed") is True:
            detail_parts.append("并且完成了当天任务")
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type == "checkin.local_saved":
        policy_key = str(payload.get("upload_policy") or "full").strip().lower()
        policy_label = TIMELINE_UPLOAD_POLICY_LABELS.get(policy_key, "完整保存")
        return "历史本地记录已保留", f"保存方式：{policy_label}"

    if event_type == "checkin.synced":
        policy_key = str(payload.get("upload_policy") or "full").strip().lower()
        policy_label = TIMELINE_UPLOAD_POLICY_LABELS.get(policy_key, "完整保存")
        return "历史记录已进入系统", f"保存方式：{policy_label}"

    if event_type == "safety.crisis_gate_opened":
        hits = payload.get("risk_hits") or []
        return "系统切换到高风险保护路径", f"命中信号：{'，'.join(str(item) for item in hits[:4])}" if hits else None

    if event_type == "report.completed":
        report_label = report_type_label(payload.get("report_type") or "daily")
        score = payload.get("health_score")
        summary = (
            f"{report_label}已生成"
            f"{f'，健康分 {score}' if score is not None else ''}"
        )
        return summary, payload.get("summary") or payload.get("suggestion")

    if event_type == "report.discarded":
        report_label = report_type_label(payload.get("report_type") or "daily")
        return f"{report_label}已随分享撤回作废", "记录恢复分享后可重新生成"

    if event_type in {"crisis.raised", "crisis.updated"}:
        level_label = risk_level_label(payload.get("level") or "none")
        score = payload.get("health_score")
        summary = f"关系状态提醒变为{level_label}"
        detail = f"关联健康分 {score}" if score is not None else None
        return summary, detail

    if event_type == "crisis.resolved":
        reason_key = str(payload.get("reason") or "").strip().lower()
        reason_label = TIMELINE_CRISIS_REASON_LABELS.get(reason_key, translate_inline_codes(reason_key))
        summary = "风险信号已解除"
        return summary, f"解除原因：{reason_label}" if reason_label else None

    if event_type == "task.generated":
        count = payload.get("task_count")
        intensity_key = str(payload.get("intensity") or "").strip().lower()
        intensity_label = TIMELINE_INTENSITY_LABELS.get(intensity_key)
        summary = f"系统生成了 {count or 0} 个行动建议"
        return summary, f"当前节奏：{intensity_label}" if intensity_label else None

    if event_type == "task.completed":
        title = payload.get("title")
        category = payload.get("category")
        category_text = task_category_label(category) if category else None
        summary = f"完成了一项行动：{title}" if title else "完成了一项行动任务"
        return summary, f"任务类别：{category_text}" if category_text else None

    if event_type in {"task.updated", "task.reopened"}:
        title = payload.get("title")
        verb = "重新打开了一项安排" if event_type == "task.reopened" else "更新了一项安排"
        summary = f"{verb}：{title}" if title else verb
        return summary, None

    if event_type == "assessment.weekly_submitted":
        total_score = payload.get("total_score")
        summary = (
            f"完成了一次关系体检，综合分 {total_score}"
            if total_score is not None
            else "完成了一次关系体检"
        )
        return summary, payload.get("change_summary")

    if event_type == "assessment.weekly_stable_band_detected":
        summary = (
            str(payload.get("summary") or "").strip()
            or "最近两次关系体检总分接近，可以先看看得分最低的项目。"
        )
        change_summary = str(payload.get("change_summary") or "").strip() or None
        return summary, change_summary

    if event_type == "attachment.analyzed":
        return "依恋倾向分析已更新", None

    if event_type == "agent.checkup.completed":
        risk_text = risk_level_label(payload.get("risk_level") or "none")
        return "完成了一次主动巡查", f"当前风险评估：{risk_text}"


    if event_type == "task.feedback_submitted":
        useful = payload.get("usefulness_score")
        friction = payload.get("friction_score")
        summary = "系统收到了这项任务的主观反馈"
        detail_parts = []
        if useful is not None:
            detail_parts.append(f"有用度 {useful}/5")
        if friction is not None:
            detail_parts.append(f"摩擦感 {friction}/5")
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type == "playbook.transitioned":
        to_branch = timeline_branch_label(payload.get("to_branch"))
        to_day = payload.get("to_day")
        summary = f"阶段节奏切到了{to_branch}"
        return summary, f"当前推进到第 {to_day} 天" if to_day else None

    if event_type == "message.simulated":
        risk_level = payload.get("risk_level")
        summary = "完成了一次发前看看"
        detail_parts = []
        if risk_level:
            detail_parts.append(f"预演状态：{risk_level_label(risk_level)}")
        if payload.get("baseline_match_label"):
            detail_parts.append(f"平时对照：{payload.get('baseline_match_label')}")
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type == "alignment.generated":
        score = payload.get("alignment_score")
        summary = "系统整理出了一版双视角对齐"
        detail_parts = []
        if score is not None:
            detail_parts.append(f"对齐分 {score}")
        sufficiency_key = str(payload.get("history_sufficiency") or "").strip().lower()
        if sufficiency_key in TIMELINE_SUFFICIENCY_LABELS:
            detail_parts.append(TIMELINE_SUFFICIENCY_LABELS[sufficiency_key])
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type in {"message.feedback_submitted", "alignment.feedback_submitted", "decision.feedback_submitted"}:
        raw_feedback = payload.get("feedback_type")
        feedback_label = payload.get("feedback_label") or (
            decision_feedback_label(raw_feedback) if raw_feedback else None
        )
        summary = "系统收到了一条纠错反馈"
        detail = f"反馈类型：{feedback_label}" if feedback_label else None
        if payload.get("note"):
            detail = f"{detail}，备注已记录" if detail else "备注已记录"
        return summary, detail

    if event_type == "plan.evaluation_snapshot":
        verdict = payload.get("verdict_label") or payload.get("verdict")
        recommendation = payload.get("recommendation_label")
        summary = f"干预效果快照已刷新{f'：{verdict}' if verdict else ''}"
        return summary, recommendation

    payload_summary = str(payload.get("summary") or "").strip()
    if payload_summary:
        return payload_summary, None

    payload_label = str(payload.get("event_label") or "").strip()
    if payload_label:
        return payload_label, None

    return timeline_event_label(event_type), None


def _translate_timeline_tag(key: str, raw_value: object) -> str | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"none", "unknown", "null"}:
        return None
    if key in {"level", "risk_level"}:
        return risk_level_label(lowered)
    if key == "plan_type":
        return plan_type_label(lowered)
    if key == "momentum":
        return TIMELINE_MOMENTUM_LABELS.get(lowered)
    if key == "intensity":
        return TIMELINE_INTENSITY_LABELS.get(lowered)
    if key == "report_type":
        return report_type_label(lowered)
    if key == "intent":
        return TIMELINE_INTENT_LABELS.get(lowered)
    if key == "category":
        return task_category_label(lowered)
    if key == "baseline_match":
        return TIMELINE_BASELINE_MATCH_LABELS.get(lowered)
    if key == "reaction_shift":
        return TIMELINE_REACTION_SHIFT_LABELS.get(lowered)
    if key == "history_sufficiency":
        return TIMELINE_SUFFICIENCY_LABELS.get(lowered)
    if key == "feedback_status":
        return DECISION_FEEDBACK_LABELS.get(lowered)
    return None


def timeline_tags_for_event(event: RelationshipEvent) -> list[str]:
    payload = event.payload or {}
    tags: list[str] = []
    for key in (
        "level",
        "risk_level",
        "plan_type",
        "momentum",
        "intensity",
        "report_type",
        "intent",
        "category",
        "baseline_match",
        "reaction_shift",
        "history_sufficiency",
        "feedback_status",
    ):
        translated = _translate_timeline_tag(key, payload.get(key))
        if translated and translated not in tags:
            tags.append(translated)
    return tags[:4]


def serialize_timeline_event(event: RelationshipEvent) -> dict:
    payload = event.payload or {}
    category = timeline_category_for_event(event.event_type)
    tone = timeline_tone_for_event(event.event_type, payload)
    summary, detail = format_timeline_summary(event)
    label = str(payload.get("event_label") or "").strip() or timeline_event_label(
        event.event_type
    )
    return {
        "id": event.id,
        "occurred_at": event.occurred_at,
        "event_type": event.event_type,
        "label": label,
        "summary": summary,
        "detail": detail,
        "category": category,
        "category_label": timeline_category_label(category),
        "tone": tone,
        "tone_label": timeline_tone_label(tone),
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "source": event.source,
        "tags": timeline_tags_for_event(event),
        "payload": payload or None,
    }


def detail_metric(label: str, value: object | None) -> dict | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return {"label": label, "value": text}


def detail_card(title: str, body: object | None, *, tone: str | None = None) -> dict | None:
    if body is None:
        return None
    text = str(body).strip()
    if not text:
        return None
    return {"title": title, "body": text, "tone": tone}


def format_bool(value: bool | None) -> str | None:
    if value is None:
        return None
    return "是" if value else "否"


async def get_latest_pair_snapshot(
    db: AsyncSession, pair_id: str
) -> RelationshipProfileSnapshot:
    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id.is_(None),
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot
    return await refresh_profile_snapshot(db, pair_id=pair_id)


async def get_latest_pair_plan(
    db: AsyncSession, pair_id: str
) -> InterventionPlan | None:
    result = await db.execute(
        select(InterventionPlan)
        .where(
            InterventionPlan.pair_id == pair_id,
            InterventionPlan.user_id.is_(None),
            InterventionPlan.status == "active",
        )
        .order_by(desc(InterventionPlan.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_completed_report(db: AsyncSession, pair_id: str) -> Report | None:
    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_completed_report_for_scope(
    db: AsyncSession, *, pair_id: str | None, user_id: str | None
) -> Report | None:
    if pair_id:
        return await get_latest_completed_report(db, pair_id)

    result = await db.execute(
        select(Report)
        .where(
            Report.user_id == user_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_dual_checkins(
    db: AsyncSession, pair: Pair
) -> tuple[Checkin | None, Checkin | None]:
    if not pair.user_b_id:
        return None, None

    result = await db.execute(
        select(Checkin)
        .where(
            Checkin.pair_id == pair.id,
            # 只有对伴侣可见的记录才能进入双方可见的派生产物（如叙事对齐）
            Checkin.visibility_scope.in_(PARTNER_VISIBLE_SCOPES),
        )
        .order_by(Checkin.checkin_date.desc(), Checkin.created_at.desc())
        .limit(40)
    )
    checkins = result.scalars().all()
    by_date: dict[str, dict[str, Checkin]] = {}
    user_a_id = str(pair.user_a_id)
    user_b_id = str(pair.user_b_id)

    for checkin in checkins:
        date_key = checkin.checkin_date.isoformat()
        bucket = by_date.setdefault(date_key, {})
        user_key = str(checkin.user_id)
        if user_key not in bucket:
            bucket[user_key] = checkin

    for date_key in sorted(by_date.keys(), reverse=True):
        bucket = by_date[date_key]
        if user_a_id in bucket and user_b_id in bucket:
            return bucket[user_a_id], bucket[user_b_id]

    return None, None


def serialize_checkin(checkin: Checkin, label: str) -> dict:
    from app.services.checkin_visibility import pair_report_content

    return {
        "label": label,
        "checkin_date": checkin.checkin_date.isoformat(),
        # shared_summary 只送过滤摘要，private 已被上游查询过滤
        "content": pair_report_content(checkin),
        "mood_score": checkin.mood_score,
        "interaction_freq": checkin.interaction_freq,
        "interaction_initiative": checkin.interaction_initiative,
        "deep_conversation": checkin.deep_conversation,
        "task_completed": checkin.task_completed,
        "sentiment_score": checkin.sentiment_score,
    }

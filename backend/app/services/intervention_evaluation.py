"""N-of-1 style evaluation for active intervention plans."""

import uuid

from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_theory import build_evaluation_theory_basis
from app.services.playbook_runtime import sync_active_playbook_runtime

RISK_ORDER = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}

VERDICT_LABELS = {
    "positive_signal": "正向信号",
    "mixed_signal": "混合信号",
    "negative_signal": "负向信号",
    "insufficient_data": "证据不足",
}

CONFIDENCE_LABELS = {
    "low": "低置信",
    "medium": "中置信",
    "high": "高置信",
}

QUALITY_LABELS = {
    "low": "低数据完备度",
    "medium": "中等数据完备度",
    "high": "高数据完备度",
}

RECOMMENDATION_LABELS = {
    "continue_current_plan": "继续当前方案",
    "adapt_plan": "调整方案强度",
    "collect_more_data": "继续观察并补数据",
    "escalate_support": "升级支持强度",
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _risk_rank(level: str | None) -> int:
    return RISK_ORDER.get(str(level or "none"), 0)


def _metric(
    *,
    metric_id: str,
    label: str,
    status: str,
    summary: str,
    baseline: str | None = None,
    current: str | None = None,
    delta: str | None = None,
    note: str | None = None,
) -> dict:
    return {
        "id": metric_id,
        "label": label,
        "status": status,
        "summary": summary,
        "baseline": baseline,
        "current": current,
        "delta": delta,
        "note": note,
    }


def _evaluate_data_quality(scorecard: dict, playbook: dict | None) -> tuple[str, list[str]]:
    duration_days = int(scorecard.get("duration_days") or 0)
    total_task_count = int(scorecard.get("total_task_count") or 0)
    feedback_count = int(scorecard.get("feedback_count") or 0)
    has_outcome_signal = (
        scorecard.get("health_delta") is not None
        or scorecard.get("risk_before") is not None
        or scorecard.get("risk_now") is not None
    )
    transition_count = int((playbook or {}).get("transition_count") or 0)

    gaps: list[str] = []
    if duration_days < 3:
        gaps.append("观察期还短，当前更像早期信号，不足以下稳定结论。")
    if total_task_count < 2:
        gaps.append("当前承载动作偏少，执行层证据还不够厚。")
    if feedback_count == 0:
        gaps.append("还缺主观有用度和执行摩擦反馈，系统难判断方案是否真的贴合。")
    if not has_outcome_signal:
        gaps.append("缺少风险或健康分变化，结果层证据仍偏弱。")
    if playbook and transition_count == 0:
        gaps.append("剧本运行态还缺少有效迁移记录，过程证据还在积累。")

    if duration_days >= 7 and total_task_count >= 4 and feedback_count >= 2 and has_outcome_signal:
        return "high", gaps
    if duration_days >= 4 and has_outcome_signal and (total_task_count >= 2 or feedback_count >= 1):
        return "medium", gaps
    return "low", gaps


def _risk_metric(scorecard: dict) -> tuple[dict, str]:
    before = str(scorecard.get("risk_before") or "none")
    now = str(scorecard.get("risk_now") or "none")
    before_rank = _risk_rank(before)
    now_rank = _risk_rank(now)

    if now_rank < before_rank:
        status = "improved"
        summary = f"风险等级从 {before} 降到 {now}，说明这轮干预至少在止损层面出现正向变化。"
    elif now_rank > before_rank:
        status = "worse"
        summary = f"风险等级从 {before} 升到 {now}，当前方案需要重新评估或升级支持。"
    else:
        status = "stable"
        summary = f"风险等级维持在 {now}，还需要结合其他指标判断这是稳定、停滞还是暂时卡住。"

    return (
        _metric(
            metric_id="risk_shift",
            label="风险变化",
            status=status,
            summary=summary,
            baseline=before,
            current=now,
            delta=f"{before} -> {now}",
        ),
        status,
    )


def _health_metric(scorecard: dict) -> tuple[dict, str]:
    before = scorecard.get("health_before")
    now = scorecard.get("health_now")
    delta = scorecard.get("health_delta")

    if before is None or now is None or delta is None:
        return (
            _metric(
                metric_id="health_shift",
                label="健康分变化",
                status="unknown",
                summary="当前还没有足够的前后健康分数据，不能只凭感觉判断方案是否有效。",
                baseline=None,
                current=None,
                delta=None,
            ),
            "unknown",
        )

    if delta >= 5:
        status = "improved"
        summary = f"健康分提升 {delta:.1f}，这是较明确的正向结果。"
    elif delta > 0:
        status = "slight_improved"
        summary = f"健康分提升 {delta:.1f}，说明关系状态在往好方向移动，但还需要继续观察稳定性。"
    elif delta < 0:
        status = "worse"
        summary = f"健康分下降 {abs(delta):.1f}，当前方案可能没有真正贴合这一轮状态。"
    else:
        status = "stable"
        summary = "健康分没有明显变化，说明这轮动作更多像在维持而不是改善。"

    return (
        _metric(
            metric_id="health_shift",
            label="健康分变化",
            status=status,
            summary=summary,
            baseline=f"{before:.1f}",
            current=f"{now:.1f}",
            delta=f"{delta:+.1f}",
        ),
        status,
    )


def _completion_metric(scorecard: dict) -> tuple[dict, str]:
    completion_rate = float(scorecard.get("completion_rate") or 0.0)
    completed = int(scorecard.get("completed_task_count") or 0)
    total = int(scorecard.get("total_task_count") or 0)

    if total == 0:
        return (
            _metric(
                metric_id="task_completion",
                label="动作完成率",
                status="unknown",
                summary="当前没有足够的承载动作，执行率证据还没建立起来。",
                baseline=None,
                current="0/0",
                delta=None,
            ),
            "unknown",
        )

    percent = round(completion_rate * 100)
    if completion_rate >= 0.67:
        status = "strong"
        summary = f"完成率 {percent}% ，说明当前方案执行阻力较低。"
    elif completion_rate >= 0.34:
        status = "fair"
        summary = f"完成率 {percent}% ，方案可以继续，但还有明显的落地损耗。"
    else:
        status = "weak"
        summary = f"完成率只有 {percent}% ，任务强度或触发时机可能不对。"

    return (
        _metric(
            metric_id="task_completion",
            label="动作完成率",
            status=status,
            summary=summary,
            baseline=None,
            current=f"{completed}/{total}",
            delta=f"{percent}%",
        ),
        status,
    )


def _fit_metric(scorecard: dict) -> tuple[dict, str]:
    usefulness = scorecard.get("usefulness_avg")
    friction = scorecard.get("friction_avg")
    feedback_count = int(scorecard.get("feedback_count") or 0)

    if feedback_count == 0 or (usefulness is None and friction is None):
        return (
            _metric(
                metric_id="subjective_fit",
                label="主观贴合度",
                status="unknown",
                summary="还没有足够的主观反馈，系统暂时无法判断用户觉得这轮动作是有帮助还是只是在硬做。",
                current="未收集",
            ),
            "unknown",
        )

    usefulness_text = f"{float(usefulness):.1f}/5" if usefulness is not None else "未收集"
    friction_text = f"{float(friction):.1f}/5" if friction is not None else "未收集"
    if usefulness is not None and friction is not None and usefulness >= 4.0 and friction <= 2.8:
        status = "good"
        summary = "主观反馈显示这轮动作既有用、又不算费劲，方案贴合度较好。"
    elif (
        (usefulness is not None and usefulness <= 2.8)
        or (friction is not None and friction >= 3.6)
    ):
        status = "poor"
        summary = "主观反馈显示这轮动作帮助感偏低或摩擦偏高，方案需要继续调轻或改写。"
    else:
        status = "mixed"
        summary = "用户能感到一定帮助，但执行体验还没有完全顺手。"

    return (
        _metric(
            metric_id="subjective_fit",
            label="主观贴合度",
            status=status,
            summary=summary,
            current=f"有用度 {usefulness_text} · 摩擦 {friction_text}",
            note=f"已收集 {feedback_count} 条反馈",
        ),
        status,
    )


def _process_metrics(scorecard: dict, playbook: dict | None) -> list[dict]:
    duration_days = int(scorecard.get("duration_days") or 0)
    total = int(scorecard.get("total_task_count") or 0)
    feedback_count = int(scorecard.get("feedback_count") or 0)
    transition_count = int((playbook or {}).get("transition_count") or 0)
    branch_changes = max(transition_count - 1, 0)
    latest_transition = (playbook or {}).get("latest_transition") or {}

    if duration_days >= 7:
        observation_status = "enough"
        observation_summary = "观察窗已经覆盖一整周，足以看出这轮方案的大致走向。"
    elif duration_days >= 3:
        observation_status = "building"
        observation_summary = "观察窗正在形成，可以判断趋势，但还不足以下强结论。"
    else:
        observation_status = "short"
        observation_summary = "观察时间太短，当前只能视为早期信号。"

    if branch_changes <= 1:
        branch_status = "stable"
        branch_summary = "剧本迁移次数不多，说明当前方案整体还算稳。"
    elif branch_changes <= 3:
        branch_status = "adaptive"
        branch_summary = "剧本正在根据反馈适度换挡，这是正常的自适应阶段。"
    else:
        branch_status = "turbulent"
        branch_summary = "剧本频繁换挡，说明当前状态波动较大或方案还没找到合适强度。"

    coverage = round((feedback_count / total) * 100) if total else 0
    if total and feedback_count / total >= 0.5:
        coverage_status = "enough"
        coverage_summary = "反馈覆盖率已经够用，系统可以更有把握地判断任务是否贴合。"
    elif total and feedback_count > 0:
        coverage_status = "partial"
        coverage_summary = "已经开始有反馈，但覆盖率还不够高。"
    else:
        coverage_status = "thin"
        coverage_summary = "当前反馈覆盖太薄，系统对真实体验的把握还有限。"

    return [
        _metric(
            metric_id="observation_window",
            label="观察窗口",
            status=observation_status,
            summary=observation_summary,
            current=f"{duration_days} 天",
        ),
        _metric(
            metric_id="branch_turbulence",
            label="分支迁移",
            status=branch_status,
            summary=branch_summary,
            current=f"{branch_changes} 次切换",
            note=latest_transition.get("trigger_summary"),
        ),
        _metric(
            metric_id="feedback_coverage",
            label="反馈覆盖",
            status=coverage_status,
            summary=coverage_summary,
            current=f"{feedback_count}/{total}" if total else "0/0",
            delta=f"{coverage}%" if total else None,
        ),
    ]


def _determine_verdict(
    *,
    data_quality: str,
    risk_status: str,
    health_status: str,
    completion_status: str,
    fit_status: str,
    risk_now: str | None,
) -> str:
    if data_quality == "low":
        return "insufficient_data"

    positive_hits = sum(
        1 for status in (risk_status, health_status, completion_status, fit_status)
        if status in ("improved", "slight_improved", "strong", "good")
    )
    negative_hits = sum(
        1 for status in (risk_status, health_status, completion_status, fit_status)
        if status in ("worse", "weak", "poor")
    )

    if str(risk_now or "none") in ("moderate", "severe") and negative_hits >= 1:
        return "negative_signal"
    if positive_hits >= 2 and negative_hits == 0:
        return "positive_signal"
    if negative_hits >= 2:
        return "negative_signal"
    return "mixed_signal"


def _determine_confidence(
    *,
    data_quality: str,
    verdict: str,
    feedback_count: int,
) -> str:
    if data_quality == "low":
        return "low"
    if data_quality == "high" and verdict in ("positive_signal", "negative_signal") and feedback_count >= 2:
        return "high"
    return "medium"


def _recommendation(
    *,
    verdict: str,
    risk_now: str | None,
    friction_avg: float | None,
) -> tuple[str, str]:
    if verdict == "positive_signal" and str(risk_now or "none") in ("none", "mild"):
        return (
            "continue_current_plan",
            "当前更像是在起效，建议先保留已经起作用的动作，再连续观察 3 天，不要太快改方向。",
        )
    if verdict == "negative_signal" and str(risk_now or "none") in ("moderate", "severe"):
        return (
            "escalate_support",
            "当前风险还在中高位，而且结果层已有负向信号，建议升级支持强度，而不是继续沿用同一套方案。",
        )
    if verdict == "insufficient_data":
        return (
            "collect_more_data",
            "现在先补 2-3 天连续记录、至少 1 条主观反馈，再来判断方案是否真的有效。",
        )
    if friction_avg is not None and float(friction_avg) >= 3.6:
        return (
            "adapt_plan",
            "当前最大问题更像是执行摩擦太高，建议先把方案调轻、调具体，而不是直接放弃。",
        )
    return (
        "adapt_plan",
        "当前结果有一部分在变好，但还不够稳定，建议继续按反馈微调任务强度和表达方式。",
    )


async def build_intervention_evaluation(
    db,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_intervention_evaluation requires exactly one scope")

    scorecard = await build_intervention_scorecard(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not scorecard:
        return None

    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        viewed=False,
    )

    data_quality, data_gaps = _evaluate_data_quality(scorecard, playbook)
    risk_metric, risk_status = _risk_metric(scorecard)
    health_metric, health_status = _health_metric(scorecard)
    completion_metric, completion_status = _completion_metric(scorecard)
    fit_metric, fit_status = _fit_metric(scorecard)
    process_metrics = _process_metrics(scorecard, playbook)

    verdict = _determine_verdict(
        data_quality=data_quality,
        risk_status=risk_status,
        health_status=health_status,
        completion_status=completion_status,
        fit_status=fit_status,
        risk_now=scorecard.get("risk_now"),
    )
    confidence = _determine_confidence(
        data_quality=data_quality,
        verdict=verdict,
        feedback_count=int(scorecard.get("feedback_count") or 0),
    )
    recommendation, recommendation_reason = _recommendation(
        verdict=verdict,
        risk_now=scorecard.get("risk_now"),
        friction_avg=scorecard.get("friction_avg"),
    )

    if verdict == "positive_signal":
        summary = "这轮干预已经出现连续正向信号，当前更应该做的是保留有效动作，而不是频繁换方案。"
    elif verdict == "negative_signal":
        summary = "这轮干预目前没有跑出有效信号，继续硬推同一套动作的收益很可能不高。"
    elif verdict == "insufficient_data":
        summary = "当前更像早期观察阶段，还不能下有效或无效的结论。"
    else:
        summary = "当前结果有好有坏，说明方案可能方向没错，但强度、时机或表达方式还要继续调。"

    next_measurements = []
    if int(scorecard.get("feedback_count") or 0) == 0:
        next_measurements.append("补至少 1 条任务主观反馈，判断动作是有用还是只是费劲。")
    if int(scorecard.get("duration_days") or 0) < 7:
        next_measurements.append("继续覆盖到至少 7 天观察窗，再判断这一轮是否稳定。")
    if int(scorecard.get("total_task_count") or 0) < 2:
        next_measurements.append("补足可执行动作，不然只能看到风险和情绪，难判断执行层是否有效。")
    if not next_measurements:
        next_measurements.append("继续监测风险、健康分和反馈覆盖，避免只凭一次好转就过早下结论。")

    return {
        "plan_id": scorecard["plan_id"],
        "pair_id": scorecard.get("pair_id"),
        "user_id": scorecard.get("user_id"),
        "plan_type": scorecard["plan_type"],
        "evaluation_model": "n_of_1_repeated_measures",
        "evaluation_label": "N-of-1 单案例重复测量",
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS[verdict],
        "confidence_level": confidence,
        "confidence_label": CONFIDENCE_LABELS[confidence],
        "data_quality_level": data_quality,
        "data_quality_label": QUALITY_LABELS[data_quality],
        "summary": summary,
        "primary_metrics": [
            risk_metric,
            health_metric,
            completion_metric,
            fit_metric,
        ],
        "process_metrics": process_metrics,
        "recommendation": recommendation,
        "recommendation_label": RECOMMENDATION_LABELS[recommendation],
        "recommendation_reason": recommendation_reason,
        "data_gaps": data_gaps[:4],
        "next_measurements": next_measurements[:4],
        "scientific_note": "这层评估采用同一段关系在干预前后做连续比较，更适合个体化产品场景，而不是直接套用群体平均结论。",
        "clinical_disclaimer": "评估结果用于帮助判断当前产品内方案是否值得继续，不是医学、心理治疗或正式临床评估结论。",
        "theory_basis": build_evaluation_theory_basis(),
    }

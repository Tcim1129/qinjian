"""Explicit theory and evidence mapping for intervention features.

This layer keeps us honest: the product can explain which parts are derived
from attachment/communication/behavioral science ideas, which are simply
engineering heuristics, and where the current boundaries are.
"""

from app.services.display_labels import model_family_label, translate_inline_codes

THEORY_LIBRARY = {
    "attachment_theory": {
        "name": "依恋理论",
        "evidence_level": "moderate",
        "evidence_label": "中等证据",
        "summary": "长期关系中的靠近、回避、威胁感知和安抚需求，往往会受依恋模式影响。",
        "boundary": "它帮助理解互动模式，不等于人格诊断，也不能替代正式心理评估。",
    },
    "gottman_repair": {
        "name": "修复尝试与冲突降级",
        "evidence_level": "practice",
        "evidence_label": "实践支持",
        "summary": "冲突里先降级、先修复连接，再谈分歧内容，通常比继续争输赢更有效。",
        "boundary": "适合一般关系冲突，不适用于暴力、胁迫、自伤他伤风险等高危场景。",
    },
    "nvc": {
        "name": "非暴力沟通结构",
        "evidence_level": "practice",
        "evidence_label": "实践支持",
        "summary": "把表达拆成事实、感受、需要、请求，能降低指责感，也更容易让对方听进去。",
        "boundary": "它是沟通结构，不保证对方一定配合，也不能单独解决长期结构性问题。",
    },
    "emotion_regulation": {
        "name": "情绪调节与降激活",
        "evidence_level": "moderate",
        "evidence_label": "中等证据",
        "summary": "高唤醒状态下先降激活，再进入问题解决，通常比情绪顶点硬谈更稳。",
        "boundary": "当存在持续失控、创伤反应或安全风险时，需要专业支持而不是只靠自助。",
    },
    "behavioral_activation": {
        "name": "行为激活与小步执行",
        "evidence_level": "moderate",
        "evidence_label": "中等证据",
        "summary": "把动作拆小、先启动再积累，会比一次给很重任务更容易形成真实执行。",
        "boundary": "它适合提升行动概率，但不代表动作越多越好，仍要看个体承载能力。",
    },
    "implementation_intentions": {
        "name": "实施意图与情境化计划",
        "evidence_level": "moderate",
        "evidence_label": "中等证据",
        "summary": "把‘什么时候、在哪儿、做什么’说具体，执行率通常会高于模糊打算。",
        "boundary": "前提是计划足够现实；若计划超出当前关系承载力，效果会迅速下降。",
    },
    "feedback_informed": {
        "name": "反馈驱动调整",
        "evidence_level": "emerging",
        "evidence_label": "新兴证据",
        "summary": "根据完成率、主观有用度和执行摩擦持续调强度，比固定方案更接近真实用户状态。",
        "boundary": "当前仍是规则引擎，不是大样本学习模型，结论应被视为持续优化中的建议。",
    },
    "n_of_1_evaluation": {
        "name": "N-of-1 单案例重复测量",
        "evidence_level": "moderate",
        "evidence_label": "中等证据",
        "summary": "在同一对象身上持续比较干预前后变化，是现实场景里很适合个体化评估的一种方法。",
        "boundary": "它能帮助看趋势和个体内变化，但不等于随机对照试验，也不适合推出普遍因果结论。",
    },
}


def _theory_card(theory_id: str, how_used: str) -> dict:
    base = THEORY_LIBRARY[theory_id]
    return {
        "id": theory_id,
        "name": base["name"],
        "evidence_level": base["evidence_level"],
        "evidence_label": base["evidence_label"],
        "summary": base["summary"],
        "how_it_is_used": how_used,
        "boundary": base["boundary"],
    }


def build_playbook_theory_basis(
    *,
    plan_type: str | None,
    branch_code: str,
) -> list[dict]:
    cards: list[dict] = [
        _theory_card(
            "feedback_informed",
            "系统会根据完成率、风险变化、主观有用度和执行摩擦，动态切换到减压、稳步、加深等分支。",
        )
    ]

    if plan_type == "conflict_repair_plan":
        cards.extend(
            [
                _theory_card(
                    "emotion_regulation",
                    "当风险升高时，剧本优先切到止损降温分支，避免在高激活状态下继续升级。",
                ),
                _theory_card(
                    "gottman_repair",
                    "冲突修复剧本强调先恢复连接，再进入具体修复动作，而不是一口气讲清全部对错。",
                ),
                _theory_card(
                    "nvc",
                    "剧本中的表达动作会尽量落在感受、需要、请求这种低攻击结构上。",
                ),
            ]
        )
    elif plan_type == "low_connection_recovery":
        cards.extend(
            [
                _theory_card(
                    "attachment_theory",
                    "低连接期优先修复安全感和可预期连接，而不是直接把任务做重。",
                ),
                _theory_card(
                    "behavioral_activation",
                    "剧本把重连动作拆成能在今天完成的小步，降低重新启动的阻力。",
                ),
                _theory_card(
                    "implementation_intentions",
                    "会把联系动作尽量具体到时间和形式，减少‘知道要做但没发生’。",
                ),
            ]
        )
    elif plan_type == "distance_compensation_plan":
        cards.extend(
            [
                _theory_card(
                    "attachment_theory",
                    "异地期更强调可预期回应和陪伴确定性，降低关系里的悬空感。",
                ),
                _theory_card(
                    "implementation_intentions",
                    "系统优先安排能兑现的远程陪伴锚点，而不是笼统要求多联系。",
                ),
                _theory_card(
                    "behavioral_activation",
                    "远程连接动作会被压缩成可完成的小活动，先保证发生，再谈升级体验。",
                ),
            ]
        )
    elif plan_type == "self_regulation_plan":
        cards.extend(
            [
                _theory_card(
                    "emotion_regulation",
                    "自我调节剧本优先做降激活、识别触发点和边界表达，不要求用户在高压下直接高质量输出。",
                ),
                _theory_card(
                    "behavioral_activation",
                    "把调节动作拆得足够小，提升开始概率和连续完成率。",
                ),
                _theory_card(
                    "implementation_intentions",
                    "会优先保留可复用的稳定动作锚点，方便在下一次状态波动时快速调用。",
                ),
            ]
        )

    if branch_code == "deepen":
        cards.append(
            _theory_card(
                "implementation_intentions",
                "当系统判断动量正在上升时，会只加半步，而不是突然加压，避免破坏已经形成的节奏。",
            )
        )
    return cards[:4]


def build_repair_protocol_theory_basis(
    *,
    protocol_type: str,
    crisis_level: str,
    active_plan_type: str | None = None,
) -> list[dict]:
    cards: list[dict] = [
        _theory_card(
            "emotion_regulation",
            "修复方案的第一优先级是把冲突强度降下来，再进入理解和修复。",
        ),
        _theory_card(
            "nvc",
            "方案里的核心动作会尽量引导到事实、感受、需要和请求，而不是标签化指责。",
        ),
        _theory_card(
            "gottman_repair",
            "系统把修复看成一系列小的修复尝试，而不是一次对话就彻底解决全部问题。",
        ),
    ]

    if crisis_level in ("mild", "none") and active_plan_type == "low_connection_recovery":
        cards.append(
            _theory_card(
                "attachment_theory",
                "当关系主问题是疏离感时，缓和建议会优先恢复被听见和被回应的体验。",
            )
        )

    if protocol_type == "de_escalation_protocol":
        cards.append(
            _theory_card(
                "feedback_informed",
                "高危状态下，系统会直接把目标从‘讲明白’切换成‘先止损’，这是安全优先的工程规则。",
            )
        )

    return cards[:4]


def build_task_strategy_theory_basis(
    *,
    plan_type: str | None,
    intensity: str,
    copy_mode: str | None,
) -> list[dict]:
    cards = [
        _theory_card(
            "behavioral_activation",
            "任务强度会按当前承载力缩放，优先保证真实执行，而不是追求看上去很完整。",
        ),
        _theory_card(
            "feedback_informed",
            "系统会把完成率、主观有用度和摩擦感作为下一轮任务调整依据。",
        ),
    ]

    if plan_type in ("low_connection_recovery", "distance_compensation_plan"):
        cards.append(
            _theory_card(
                "implementation_intentions",
                "关系任务会尽量落到具体时间、场景和动作，帮助用户从‘想做’走到‘真的发生’。",
            )
        )
    if plan_type == "conflict_repair_plan":
        cards.append(
            _theory_card(
                "nvc",
                "修复类任务会优先推荐低攻击、可复述的表达结构，减少冲突再次升级。",
            )
        )
    if copy_mode in ("gentle", "clear", "compact", "example"):
        cards.append(
            _theory_card(
                "attachment_theory",
                "任务文案会根据反馈改成更温和、更具体或带示例的表达，以贴合不同人的接收方式。",
            )
        )
    return cards[:4]


def build_methodology_summary(
    *,
    plan_type: str | None,
    is_pair: bool,
) -> dict:
    active_modules = ["事件流", "画像快照", "干预评分卡", "剧本运行态"]
    if is_pair:
        active_modules.extend(["冲突修复方案", "双人任务调度"])
    else:
        active_modules.append("自我调节任务调度")

    if plan_type == "conflict_repair_plan":
        focus = ["先降温", "再对齐理解", "最后落修复动作"]
    elif plan_type == "low_connection_recovery":
        focus = ["先恢复可预期连接", "再提升深聊质量", "最后保留小仪式"]
    elif plan_type == "distance_compensation_plan":
        focus = ["先固定远程锚点", "再增加共同体验", "最后维持期待感"]
    else:
        focus = ["先稳住状态", "再识别触发点", "最后练习边界与表达"]

    return {
        "system_name": "relationship_intervention_system_v1",
        "system_name_label": "关系行为干预系统第一版",
        "model_family": "rule_engine_with_feedback_loop",
        "model_family_label": model_family_label("rule_engine_with_feedback_loop"),
        "measurement_model": [
            "每日打卡与情绪/互动指标",
            "关系任务完成率",
            "主观有用度与执行摩擦",
            "风险等级与健康分趋势",
            "消息模拟与双视角的纠错反馈",
        ],
        "decision_model": [
            "先抽取稳定信号，再进入评分层",
            "只让文案层组织表达，不改核心分层",
            "根据完成率和反馈切剧本分支",
            "根据计划类型切换任务与修复策略",
        ],
        "active_modules": active_modules,
        "current_focus": [translate_inline_codes(item) for item in focus],
        "disclaimer": "当前系统是基于关系心理学和行为科学启发的工程化决策系统，不是医学诊断、临床治疗或正式心理测评工具。当前判断支持版本化回放与反馈闭环，但仍需结合人工复核。",
    }


def build_evaluation_theory_basis() -> list[dict]:
    return [
        _theory_card(
            "n_of_1_evaluation",
            "系统把同一段关系在计划开始前后的风险、健康分、执行率和反馈放到同一条时间线上做个体内比较。",
        ),
        _theory_card(
            "feedback_informed",
            "结论不会只看单次完成，而会结合主观有用度、执行摩擦和分支切换情况判断是否继续当前方案。",
        ),
    ]

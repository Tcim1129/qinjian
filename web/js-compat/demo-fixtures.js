window.QJ_DEMO_FIXTURE = {
  me: {
    id: "11111111-1111-4111-8111-111111111111",
    email: "demo@qinjian.local",
    nickname: "陈一",
    created_at: "2026-02-02T09:00:00"
  },
  currentPairId: "22222222-2222-4222-8222-222222222222",
  pairs: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      user_a_id: "11111111-1111-4111-8111-111111111111",
      user_b_id: "33333333-3333-4333-8333-333333333333",
      type: "couple",
      status: "active",
      invite_code: "628531",
      partner_nickname: "林夏",
      partner_email: "linxia@demo.local",
      custom_partner_nickname: "林夏",
      created_at: "2026-02-14T20:00:00"
    }
  ],
  notifications: [
    {
      id: "44444444-4444-4444-8444-444444444444",
      type: "system",
      content: "样例模式已启用，当前页面仅供查看。",
      is_read: false,
      created_at: "2026-03-21T09:30:00"
    }
  ],
  todayStatus: {
    pair_id: "22222222-2222-4222-8222-222222222222",
    my_done: true,
    partner_done: true,
    both_done: true,
    has_report: true,
    my_checkin: {
      mood_score: 3,
      interaction_freq: 2,
      deep_conversation: true,
      content: "昨晚其实有点委屈，但我们终于把“为什么会觉得被忽略”说清楚了一点。"
    }
  },
  streak: {
    streak: 6
  },
  tree: {
    level_name: "稳定修复期",
    growth_points: 148,
    progress_percent: 57
  },
  crisis: {
    crisis_level: "moderate",
    intervention: {
      title: "先按修复协议降温，再做一个低摩擦修复动作。",
      description: "当前阶段更适合低刺激修复，不适合一次性谈清全部问题。"
    }
  },
  tasks: {
    combination_insight: "系统建议先稳住表达刺激性，再安排一个可执行的小修复动作。",
    tasks: [
      {
        id: "task-demo-1",
        title: "先发一条低刺激说明",
        description: "先说感受，再说一个具体需求，不急着把所有问题一次讲完。",
        category: "repair",
        status: "pending",
        copy_mode: "gentle",
        copy_mode_source: "category"
      },
      {
        id: "task-demo-2",
        title: "今晚约 10 分钟短通话",
        description: "把目标放在确认彼此是否还在同一频道，而不是立刻讨论全部旧问题。",
        category: "connection",
        status: "pending"
      },
      {
        id: "task-demo-3",
        title: "记录这轮动作是否有效",
        description: "明天回到系统里补一条反馈，给下一轮策略判断留下证据。",
        category: "reflection",
        status: "completed",
        feedback: {
          usefulness_score: 4,
          note: "上一次这样做后，对方没有再直接升级。"
        },
        needs_feedback: false
      }
    ]
  },
  milestones: [
    {
      id: "milestone-demo-1",
      title: "下次视频复盘",
      type: "custom",
      days_until: 2,
      target_date: "2026-03-25",
      note: "用双视角对齐结果复盘这轮修复是否真的起效。"
    }
  ],
  adminPolicies: [
    {
      policy_id: "conflict-soften-v3",
      plan_type: "conflict_repair_plan",
      title: "先降压后表达",
      summary: "先稳定情绪和节奏，再进入结构化修复。",
      status: "active",
      version: "v3.2"
    },
    {
      policy_id: "reconnect-steady-v2",
      plan_type: "low_connection_recovery",
      title: "轻量重连版",
      summary: "先恢复连接，再提高互动强度。",
      status: "active",
      version: "v2.4"
    },
    {
      policy_id: "distance-repair-v1",
      plan_type: "distance_compensation_plan",
      title: "异地补偿版",
      summary: "适合异地低互动阶段的补偿剧本。",
      status: "inactive",
      version: "v1.8"
    }
  ],
  safetyStatus: {
    risk_level: "moderate",
    why_now: "最近连续出现高风险消息预演、连接下降和风险提醒，所以系统先强调边界与止损，而不是继续鼓励强推进。",
    evidence_summary: [
      "最近一份关系简报健康分为 78/100，但风险区间仍停留在中度。",
      "近 7 天互动重合率约为 42%，说明连接没有完全断开，但仍偏脆弱。",
      "最近已有 2 次高风险消息预演，说明表达方式仍可能触发误解或升级。",
      "当前仍有一条激活中的冲突修复计划，目标是先恢复安全沟通窗口。"
    ],
    limitation_note: "本次判断基于最近的打卡、简报、任务反馈和风险事件，它是关系支持系统，不等于对对方意图或安全状况的临床判断。",
    recommended_action: "先按修复协议降温，再做一个低摩擦的小修复动作，而不是追求一次谈清全部问题。",
    handoff_recommendation: "如果已经出现持续升级、威胁、羞辱、断联试探或任何安全担忧，请停止依赖产品内建议，转向可信任的人、专业咨询或当地紧急支持。"
  },
  assessmentTrend: {
    latest_score: 74,
    dimension_scores: [
      { id: "connection", label: "连接与表达", score: 72, status: "watch" },
      { id: "trust", label: "信任与安全", score: 76, status: "strong" },
      { id: "repair", label: "修复能力", score: 61, status: "watch" },
      { id: "shared_future", label: "共同愿景", score: 81, status: "strong" },
      { id: "vitality", label: "关系活力", score: 78, status: "strong" }
    ],
    trend_points: [
      { event_id: "55555555-5555-4555-8555-555555555551", submitted_at: "2026-02-28T21:00:00", total_score: 62, scope: "pair", change_summary: "这是第一份正式周评估。", dimension_scores: [] },
      { event_id: "55555555-5555-4555-8555-555555555552", submitted_at: "2026-03-07T21:00:00", total_score: 68, scope: "pair", change_summary: "相比上一轮有小幅改善。", dimension_scores: [] },
      { event_id: "55555555-5555-4555-8555-555555555553", submitted_at: "2026-03-14T21:00:00", total_score: 71, scope: "pair", change_summary: "相比上一轮略有改善。", dimension_scores: [] },
      { event_id: "55555555-5555-4555-8555-555555555554", submitted_at: "2026-03-21T21:00:00", total_score: 74, scope: "pair", change_summary: "相比上一轮有小幅改善。", dimension_scores: [] }
    ],
    change_summary: "最近 4 次正式周评估整体回升，说明关系体验正在回暖，但修复能力仍是最需要继续追踪的维度。"
  },
  latestReport: {
    id: "66666666-6666-4666-8666-666666666666",
    pair_id: "22222222-2222-4222-8222-222222222222",
    type: "daily",
    status: "completed",
    report_date: "2026-03-21",
    created_at: "2026-03-21T22:10:00",
    health_score: 78,
    evidence_summary: [
      "最近简报健康分为 78/100。",
      "最近 7 天互动重合率在 42% 左右。",
      "消息预演的高风险次数仍偏高。"
    ],
    limitation_note: "报告结论基于最近记录与事件流，不等于临床判断。",
    safety_handoff: "如果争执已经持续升级，请停止继续硬聊，改为降温或寻求线下支持。",
    content: {
      health_score: 78,
      crisis_level: "moderate",
      insight: "你们并不是没有连接，而是最近每次想靠近的时候，都更容易先被压力接住。",
      suggestion: "今天最合适的不是谈完全部问题，而是先把一句低刺激的话说清楚。",
      encouragement: "只要先把节奏慢下来，很多误会并不会真的走到最坏。",
      highlights: [
        "这周双方都没有完全退出关系，仍愿意继续回应。",
        "共同愿景和长期目标感仍然稳定存在。",
        "最近一次修复动作后，情绪恢复速度比上周更快。"
      ],
      concerns: [
        "高压力表达仍会触发对方的防御和退避。",
        "修复窗口经常开得太晚，容易从误会拖成争执。",
        "异地状态下，文字沟通承压时更容易被误读。"
      ],
      trend_description: "整体走势在变好，但系统建议继续维持低刺激修复节奏。",
      professional_note: "当前仍更适合先止损再推进，不建议强行一次性谈清。"
    }
  },
  reportHistory: [
    { id: "66666666-6666-4666-8666-666666666664", type: "daily", status: "completed", report_date: "2026-03-19", created_at: "2026-03-19T22:05:00", health_score: 71, content: { insight: "这两天最难的不是没有感情，而是修复总是慢半拍。" } },
    { id: "66666666-6666-4666-8666-666666666665", type: "daily", status: "completed", report_date: "2026-03-20", created_at: "2026-03-20T22:06:00", health_score: 75, content: { insight: "互动开始回暖，但系统仍在观察是否会再次被高刺激表达打断。" } },
    { id: "66666666-6666-4666-8666-666666666666", type: "daily", status: "completed", report_date: "2026-03-21", created_at: "2026-03-21T22:10:00", health_score: 78, content: { insight: "你们并不是没有连接，而是最近每次想靠近的时候，都更容易先被压力接住。" } }
  ],
  healthTrend: {
    trend: [
      { date: "2026-03-15", score: 64 },
      { date: "2026-03-16", score: 66 },
      { date: "2026-03-17", score: 68 },
      { date: "2026-03-18", score: 70 },
      { date: "2026-03-19", score: 71 },
      { date: "2026-03-20", score: 75 },
      { date: "2026-03-21", score: 78 }
    ],
    direction: "improving",
    days: 14
  },
  policyAudit: {
    plan_id: "77777777-7777-4777-8777-777777777777",
    pair_id: "22222222-2222-4222-8222-222222222222",
    plan_type: "conflict_repair_plan",
    audit_label: "Decision Audit",
    decision_model: "rules_plus_feedback_loop",
    current_policy: { policy_id: "conflict-soften-v3", title: "先降压后表达" },
    recommended_policy: { policy_id: "conflict-soften-v3", title: "继续保持当前低刺激策略" },
    selection_mode: "hold",
    selection_label: "谨慎保持",
    selection_reason: "最近连续 2 次消息预演偏高风险，所以系统保持“先降压后表达”，避免过早切回高强度修复。",
    schedule_mode: "observe",
    schedule_label: "72 小时观察",
    schedule_summary: "再观察 2 次任务反馈和 1 次正式周评估后决定是否推进。",
    active_branch_label: "减压保节奏",
    next_checkpoint: "2026-03-24",
    evidence_observation_count: 6,
    signals: [
      { id: "sim-risk", label: "高风险消息预演", current: "2 次", target: "降到 0-1 次", why: "如果表达方式还容易刺痛对方，系统不会贸然提高策略强度。" },
      { id: "repair-friction", label: "任务摩擦", current: "2.8/5", target: "≤ 2.5/5", why: "当前更适合先做小动作，而不是要求一次解决全部问题。" }
    ],
    supporting_events: [
      { id: "88888888-8888-4888-8888-888888888881", event_type: "message.simulated", category: "coach", category_label: "教练", tone: "support", tone_label: "辅助理解", occurred_at: "2026-03-21T20:40:00", label: "聊天前预演提示风险偏高", summary: "一句带指责色彩的话很可能先被对方当成压力，而不是需求。", detail: "系统因此没有把策略切到更高强度的修复分支。", tags: ["高风险", "建议改写"] },
      { id: "88888888-8888-4888-8888-888888888882", event_type: "task.feedback_submitted", category: "action", category_label: "行动", tone: "progress", tone_label: "正在推进", occurred_at: "2026-03-20T22:30:00", label: "任务反馈显示“有用但仍有摩擦”", summary: "说明这轮策略开始有效，但还不适合突然加压。", detail: "系统选择继续保持低刺激表达版本。", tags: ["反馈", "摩擦"] }
    ],
    decision_history: [
      { occurred_at: "2026-03-21T22:12:00", summary: "保持当前策略版本，等待下一次检查点。", selection_mode: "hold", selection_label: "谨慎保持", schedule_mode: "observe", schedule_label: "72 小时观察", selected_policy_signature: "conflict-soften-v3", selected_policy_label: "先降压后表达", auto_applied: true, checkpoint_date: "2026-03-24" },
      { occurred_at: "2026-03-19T22:08:00", summary: "从“结构化修复”切回“减压保节奏”，优先防止继续升级。", selection_mode: "backoff", selection_label: "自动回退", schedule_mode: "reset", schedule_label: "重置观察窗", selected_policy_signature: "conflict-soften-v3", selected_policy_label: "先降压后表达", auto_applied: true, checkpoint_date: "2026-03-21" }
    ],
    scientific_note: "当前系统使用规则引擎、单案例重复测量和反馈闭环来判断何时保持、减压或推进。",
    clinical_disclaimer: "该面板用于解释系统如何做出策略决策，不替代专业咨询或安全评估。"
  },
  playbook: {
    plan_id: "77777777-7777-4777-8777-777777777777",
    run_id: "99999999-9999-4999-8999-999999999999",
    run_status: "active",
    plan_type: "conflict_repair_plan",
    title: "7 天修复剧本",
    summary: "先降温、再表达、再确认下一步，不靠一次对话赌赢修复。",
    primary_goal: "先恢复安全沟通窗口，再决定是否推进深层问题。",
    momentum: "steady",
    risk_level: "moderate",
    active_branch: "decompress",
    active_branch_label: "减压保节奏",
    branch_reason: "最近仍有高风险表达和中度风险提醒，所以系统把今天放在低刺激修复分支。",
    focus_tags: ["先降温", "低刺激表达", "异地沟通"],
    model_family: "rule_engine_with_feedback_loop",
    clinical_disclaimer: "剧本用于日常关系支持，不替代专业支持。",
    current_day: 3,
    total_days: 7,
    transition_count: 2,
    branch_started_at: "2026-03-19T22:08:00",
    last_synced_at: "2026-03-21T22:10:00",
    latest_transition: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", transition_type: "branch_shift", trigger_type: "message.simulation", trigger_summary: "消息预演再次出现高风险，系统保持减压分支并延长观察期。", from_day: 2, to_day: 3, from_branch: "repair", from_branch_label: "按计划推进", to_branch: "decompress", to_branch_label: "减压保节奏", created_at: "2026-03-19T22:08:00", is_new: false },
    today_card: { day_index: 3, label: "第 3 天", title: "先做低刺激修复动作", theme: "降温先行", objective: "避免再次升级，重新建立安全沟通窗口。", action: "先发一条低刺激说明，再约一个 10 分钟短通话。", success_signal: "对方愿意继续回应，并没有再次升级。", checkin_prompt: "今晚哪一句表达最让你感觉到“被接住”，哪一句又差点升级？", branch_mode: "decompress", branch_mode_label: "减压保节奏", status: "today" },
    days: [
      { day_index: 1, label: "第 1 天", title: "暂停高刺激对话", theme: "止损", objective: "先停止升级", action: "把目标从讲清全部问题改成先停下来。", branch_mode: "decompress", branch_mode_label: "减压保节奏", status: "done" },
      { day_index: 2, label: "第 2 天", title: "先说感受，再说需求", theme: "重建表达", objective: "降低指责感", action: "改写一句最想说的话，只保留一个具体需求。", branch_mode: "decompress", branch_mode_label: "减压保节奏", status: "done" },
      { day_index: 3, label: "第 3 天", title: "先做低刺激修复动作", theme: "降温先行", objective: "避免再次升级，重新建立安全沟通窗口。", action: "先发一条低刺激说明，再约一个 10 分钟短通话。", branch_mode: "decompress", branch_mode_label: "减压保节奏", status: "today" },
      { day_index: 4, label: "第 4 天", title: "确认对齐程度", theme: "轻量复盘", objective: "看看双方是否听懂彼此重点。", action: "用双视角对齐结果，复述一次彼此真正关心的点。", branch_mode: "steady", branch_mode_label: "按计划推进", status: "upcoming" }
    ],
    theory_basis: []
  },
  scorecard: {
    plan_id: "77777777-7777-4777-8777-777777777777",
    pair_id: "22222222-2222-4222-8222-222222222222",
    plan_type: "conflict_repair_plan",
    status: "active",
    risk_level: "moderate",
    primary_goal: "先恢复安全沟通窗口，再推进深层修复。",
    focus: ["降温", "修复", "异地"],
    start_date: "2026-03-18",
    end_date: "2026-03-25",
    duration_days: 7,
    risk_before: "severe",
    risk_now: "moderate",
    health_before: 66,
    health_now: 78,
    health_delta: 12,
    completion_rate: 0.67,
    completed_task_count: 4,
    total_task_count: 6,
    feedback_count: 3,
    usefulness_avg: 4.1,
    friction_avg: 2.8,
    momentum: "steady",
    wins: ["最近 2 次沟通没有再直接升级。"],
    watchouts: ["一旦文字表达带责备意味，局面仍可能重新升温。"],
    next_actions: ["继续保持低刺激表达，再观察 72 小时。"]
  },
  policySchedule: {
    plan_id: "77777777-7777-4777-8777-777777777777",
    pair_id: "22222222-2222-4222-8222-222222222222",
    plan_type: "conflict_repair_plan",
    scheduler_model: "rule_scheduler",
    scheduler_label: "策略排期器",
    schedule_mode: "observe",
    schedule_label: "72 小时观察",
    current_policy: { policy_id: "conflict-soften-v3", title: "先降压后表达" },
    current_stage: { phase: "observe", phase_label: "观察期", title: "先观察，不急着升级强度", summary: "连续 72 小时没有再升级，再考虑切回更积极的修复版本。", policy_id: "conflict-soften-v3", days_total: 7, days_observed: 3, days_remaining: 4, min_observations: 3, observations_remaining: 0, checkpoint_date: "2026-03-24", branch_label: "减压保节奏", intensity_label: "低刺激", copy_mode_label: "更温和" },
    next_stage: { phase: "advance", phase_label: "推进期", title: "如果继续稳定，再回到结构化修复", summary: "到检查点后若风险继续下降，就可以切回按计划推进分支。", policy_id: "conflict-soften-v3", days_total: 7, days_observed: 0, days_remaining: 0, min_observations: 0, observations_remaining: 0, checkpoint_date: "2026-03-24", branch_label: "按计划推进", intensity_label: "稳定推进", copy_mode_label: "更具体" },
    fallback_stage: null,
    measurement_plan: [
      { id: "risk", label: "高风险预演", current: "2 次", target: "0-1 次", why: "观察表达是否更稳。" },
      { id: "friction", label: "任务摩擦", current: "2.8/5", target: "≤ 2.5/5", why: "观察任务是否更容易执行。" }
    ],
    advance_when: ["接下来 72 小时没有再次升级。"],
    hold_when: ["仍有轻微防御，但可以继续对话。"],
    backoff_when: ["再次出现高风险消息预演或明显失控。"],
    scientific_note: "排期器会把分支、强度和观察窗统一安排。",
    clinical_disclaimer: "排期用于日常支持，不替代专业判断。"
  },
  messageSimulation: {
    draft: "你今天怎么又这么晚才回我，我真的很烦。",
    partner_view: "对方很可能先听成“你又做错了”，而不是“我现在有点受伤”。",
    likely_impact: "如果直接发送，接下来更可能进入解释、防御或沉默，而不是修复。",
    risk_level: "high",
    risk_reason: "这句话把情绪和指责绑在一起，对方更容易先感到压力，而不是看见你的真实需求。",
    safer_rewrite: "我刚刚有点失落，因为等了很久都没收到你的消息。你忙的时候如果能先告诉我一声，我会安心很多。",
    suggested_tone: "低刺激",
    conversation_goal: "先让对方接住你的感受",
    do_list: ["先说自己的感受，再说一个具体需求。", "一次只说一个点，不要顺手翻旧账。", "把目标放在重新建立沟通窗口，而不是马上讲赢。"],
    avoid_list: ["避免“你怎么又”这类绝对化开头。", "不要把等待感直接写成指责。", "不要在情绪顶点继续加长句。"],
    evidence_summary: ["最近已有 2 次高风险消息预演。", "当前仍处在中度风险区间。", "当前策略要求优先降低表达刺激性。"],
    limitation_note: "预演只基于最近关系画像和事件流，不等于对对方真实反应的绝对预测。",
    safety_handoff: "如果这次沟通已经多次升级，请先不要发送，改为暂停、降温，必要时转向人工支持。"
  },
  narrativeAlignment: {
    pair_id: "22222222-2222-4222-8222-222222222222",
    checkin_date: "2026-03-21",
    user_a_label: "陈一",
    user_b_label: "林夏",
    alignment_score: 71,
    shared_story: "你们都在乎这段关系，只是最近一个人在努力确认“我还重要吗”，另一个人在努力证明“我不是不在乎，只是太累了”。",
    view_a_summary: "你更在意被及时回应，因为延迟会被你接成自己不被在乎。",
    view_b_summary: "对方更像是在疲惫和压力里撤退，并不是真的想退出关系。",
    misread_risk: "最容易错位的点是：你的追问在对方那里会先被听成压力，而不是需要靠近。",
    divergence_points: ["你以为自己是在确认连接，对方感受到的是再次被要求交代。", "对方以为沉默是在避免升级，你感受到的却是被抛下。"],
    bridge_actions: ["先用一句低刺激感受表达开头，不要直接追问。", "先确认对方是否有 10 分钟空档，再进入主题。", "只对齐一个误解点，不要顺手扩展到所有旧问题。"],
    suggested_opening: "我不是想和你算账，我只是想把刚刚那点失落说清楚，看看我们能不能找到一个更不累的沟通方式。",
    coach_note: "这次先对齐“彼此其实都没想退出”这一点，会比直接争谁更委屈更有帮助。",
    current_risk_level: "moderate",
    active_plan_type: "conflict_repair_plan",
    generated_at: "2026-03-21T22:15:00"
  },
  repairProtocol: {
    protocol_type: "structured_repair",
    level: "moderate",
    title: "中度冲突修复协议",
    summary: "当前更适合先降温、再用结构化表达回到同一频道，而不是继续硬谈到底。",
    timing_hint: "先用文字铺垫，再约一个 10 分钟短通话。",
    active_plan_type: "conflict_repair_plan",
    model_family: "rule_engine_with_safety_first",
    clinical_disclaimer: "修复协议用于一般沟通冲突，不替代法律、医疗或专业心理支持。",
    focus_tags: ["异地", "冲突修复", "低刺激"],
    theory_basis: [],
    steps: [
      { sequence: 1, title: "先停 10-20 分钟", action: "先不继续追问，让情绪从顶点降下来。", why: "避免把修复再次打成争执。", duration_hint: "10-20 分钟" },
      { sequence: 2, title: "只说一个点", action: "先说刚刚最让你失落的一件事，不顺手翻出第二个问题。", why: "越聚焦，对方越容易接住。", duration_hint: "2 分钟" },
      { sequence: 3, title: "先讲感受，再讲需求", action: "用“我刚刚有点失落，因为……”代替“你怎么又……”。", why: "能显著降低对方的防御感。", duration_hint: "2 分钟" },
      { sequence: 4, title: "约一个小动作", action: "最后只确认一个今晚就能做到的小调整。", why: "把修复落成动作，而不是只停在道理。", duration_hint: "1 分钟" }
    ],
    do_not: ["不要继续翻旧账。", "不要逼对方立刻给出最终结论。", "不要在失控时做重大决定。"],
    success_signal: "对方愿意继续回应，并能确认一个小的下一步。",
    escalation_rule: "如果再次出现明显升级、羞辱或断联试探，请暂停产品内修复，直接寻求人工支持。",
    evidence_summary: ["当前风险等级为 moderate，修复节奏需要以止损优先。", "最近仍有高风险消息预演，所以协议保持低刺激结构。", "当前仍有一条冲突修复计划在执行。"],
    limitation_note: "修复协议基于最近风险等级、关系画像和当前计划生成，它帮助双方降温和重建沟通，不替代专业判断。",
    safety_handoff: "如果已经出现持续升级、威胁、羞辱、肢体伤害风险或明显失控，请停止继续推进对话，转向可信任的人、专业咨询或当地紧急支持。"
  },
  timeline: {
    event_count: 6,
    latest_event_at: "2026-03-21T22:15:00",
    highlights: ["高风险表达次数下降", "修复动作开始起效", "策略仍保持低刺激版本"],
    events: [
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1", event_type: "report.completed", category: "report", category_label: "洞察", tone: "insight", tone_label: "得到洞察", occurred_at: "2026-03-21T22:10:00", label: "新简报生成完成", summary: "系统给出一句结论：你们不是没有连接，而是每次靠近前都容易先被压力接住。", detail: "它解释了为什么现在更适合先降温，再谈更深层的点。", tags: ["健康 78", "中等风险"] },
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2", event_type: "message.simulated", category: "coach", category_label: "教练", tone: "support", tone_label: "辅助理解", occurred_at: "2026-03-21T20:40:00", label: "聊天前预演提示高风险", summary: "原始表达很可能先被对方接成压力，而不是你的真实需求。", detail: "系统因此继续保持低刺激策略版本。", tags: ["高风险", "建议改写"] },
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb3", event_type: "repair_protocol.requested", category: "risk", category_label: "风险", tone: "warning", tone_label: "需要留意", occurred_at: "2026-03-21T20:45:00", label: "修复协议被请求", summary: "当前阶段更适合中度冲突修复协议，而不是继续高强度推进。", detail: "系统把目标放在重新建立安全沟通窗口。", tags: ["中等风险", "修复"] },
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb4", event_type: "task.feedback_submitted", category: "action", category_label: "行动", tone: "progress", tone_label: "正在推进", occurred_at: "2026-03-20T22:30:00", label: "任务反馈已回收", summary: "这轮动作被评价为“有用但仍有一点摩擦”。", detail: "说明策略开始起效，但还不适合立刻加压。", tags: ["反馈", "摩擦 2.8"] },
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb5", event_type: "playbook.transitioned", category: "playbook", category_label: "剧本", tone: "movement", tone_label: "状态切换", occurred_at: "2026-03-19T22:08:00", label: "7 天剧本切到减压分支", summary: "系统把当前剧本从“按计划推进”切回“减压保节奏”。", detail: "原因是高风险表达再次出现，必须先防止继续升级。", tags: ["路径切换", "减压"] },
      { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb6", event_type: "assessment.weekly_submitted", category: "system", category_label: "体检", tone: "insight", tone_label: "得到洞察", occurred_at: "2026-03-21T21:00:00", label: "正式周评估已提交", summary: "近 4 次关系体检显示总分持续回升，但修复能力仍是最低维度。", detail: "这也是系统保持当前策略的一个关键原因。", tags: ["得分 74", "关注修复"] }
    ]
  },
  timelineEventDetails: {
    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1": {
      event: { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1", event_type: "report.completed", category: "report", category_label: "洞察", tone: "insight", tone_label: "得到洞察", occurred_at: "2026-03-21T22:10:00", label: "新简报生成完成", summary: "系统给出一句结论：你们不是没有连接，而是每次靠近前都容易先被压力接住。", detail: "它解释了为什么现在更适合先降温，再谈更深层的点。", tags: ["健康 78", "中等风险"] },
      event_summary: "这份简报把最近的记录、风险和修复节奏压缩成了一句更容易理解的当前判断。",
      metrics: [
        { id: "health", label: "健康分", value: "78/100", summary: "比上周提高 12 分。" },
        { id: "risk", label: "当前风险", value: "中等", summary: "仍未退出需要边界说明的区间。" }
      ],
      evidence_cards: [
        { id: "insight", title: "简报一句结论", body: "你们不是没有连接，而是最近每次想靠近的时候，都更容易先被压力接住。", tone: "insight" },
        { id: "next", title: "这为什么重要", body: "它决定了系统先给降温与低刺激表达，而不是继续加压修复。", tone: "neutral" }
      ],
      impact_modules: ["关系简报", "策略判断", "修复协议", "时间轴证据"],
      recommended_next_action: "先做一个低摩擦修复动作，再观察下一次正式周评估。",
      current_context: {
        active_plan_type: "conflict_repair_plan",
        active_branch_label: "减压保节奏",
        momentum: "steady",
        risk_level: "moderate",
        latest_report_insight: "先降温，再推进。",
        recommended_next_action: "先做一个低摩擦修复动作。"
      }
    }
  }
};

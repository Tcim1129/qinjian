export const DEMO_TOKEN = 'demo-mode'

const DEMO_EMAIL = 'demo@qinjian.local'

export const demoFixture = {
  me: {
    id: '11111111-1111-4111-8111-111111111111',
    email: DEMO_EMAIL,
    nickname: '陈一',
    ai_assist_enabled: true,
    privacy_mode: 'cloud',
    preferred_entry: 'daily',
    preferred_language: 'zh',
    tone_preference: 'gentle',
    response_length: 'medium',
    relationship_space_theme: 'classic',
    living_region: '上海',
    habit_profile: {
      taboos: ['反感长篇说教', '疲惫时不喜被追问细节', '讨厌做家务时居高临下邀功'],
      comfort_preferences: ['疲惫时只要安静陪伴', '有事直接给解决方案不用绕弯'],
      custom_notes: '加班很晚回家后需要先发呆20分钟放空，不要立刻跟我谈复杂事情。',
    },
    created_at: '2026-02-02T09:00:00',
  },
  currentPairId: '22222222-2222-4222-8222-222222222222',
  pairs: [
    {
      id: '22222222-2222-4222-8222-222222222222',
      user_a_id: '11111111-1111-4111-8111-111111111111',
      user_b_id: '33333333-3333-4333-8333-333333333333',
      type: 'couple',
      status: 'active',
      invite_code: 'A3H7K8M9Q2',
      partner_nickname: '林夏',
      partner_email: 'linxia@demo.local',
      custom_partner_nickname: '林夏',
      created_at: '2026-02-14T20:00:00',
    },
    {
      id: '77777777-7777-4777-8777-777777777777',
      user_a_id: '11111111-1111-4111-8111-111111111111',
      user_b_id: '88888888-8888-4888-8888-888888888888',
      type: 'friend',
      status: 'active',
      invite_code: 'B4J8L9N2P3',
      partner_nickname: '周宁',
      partner_email: 'zhouning@demo.local',
      custom_partner_nickname: '周宁',
      latest_change_request: {
        id: '77770000-7777-4777-8777-777777777777',
        pair_id: '77777777-7777-4777-8777-777777777777',
        kind: 'break_request',
        kind_label: '移除关系',
        status: 'rejected',
        status_label: '已恢复',
        requester_user_id: '11111111-1111-4111-8111-111111111111',
        requester_nickname: '陈一',
        approver_user_id: '88888888-8888-4888-8888-888888888888',
        approver_nickname: '周宁',
        requested_by_me: true,
        waiting_for_me: false,
        allow_retention: true,
        phase: 'retaining',
        expires_at: '2026-04-22T21:30:00',
        resolution_reason: 'retention_accepted',
        messages: [
          {
            id: '77771111-7777-4777-8777-777777777777',
            sender_user_id: '88888888-8888-4888-8888-888888888888',
            sender_nickname: '周宁',
            message: '我不想就这样结束，我们先把最近卡住的地方说清楚。',
            created_at: '2026-04-22T09:45:00',
          },
          {
            id: '77772222-7777-4777-8777-777777777777',
            sender_user_id: '88888888-8888-4888-8888-888888888888',
            sender_nickname: '周宁',
            message: '如果你愿意，我会先把之前答应的事补上。',
            created_at: '2026-04-22T11:20:00',
          },
        ],
        created_at: '2026-04-22T09:30:00',
        decided_at: '2026-04-22T12:10:00',
      },
      created_at: '2026-03-08T18:20:00',
    },
    {
      id: '99999999-9999-4999-8999-999999999999',
      user_a_id: '11111111-1111-4111-8111-111111111111',
      user_b_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      type: 'friend',
      status: 'active',
      invite_code: 'C5K9M2Q4R7',
      partner_nickname: '顾遥',
      partner_email: 'guyao@demo.local',
      custom_partner_nickname: '顾遥',
      pending_change_request: {
        id: '99990000-9999-4999-8999-999999999999',
        pair_id: '99999999-9999-4999-8999-999999999999',
        kind: 'break_request',
        kind_label: '移除关系',
        status: 'pending',
        status_label: '待对方决定',
        requester_user_id: '11111111-1111-4111-8111-111111111111',
        requester_nickname: '陈一',
        approver_user_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        approver_nickname: '顾遥',
        requested_by_me: true,
        waiting_for_me: false,
        allow_retention: true,
        phase: 'awaiting_retention_choice',
        expires_at: '2026-04-24T10:00:00',
        resolution_reason: null,
        messages: [],
        created_at: '2026-04-23T10:00:00',
        decided_at: null,
      },
      created_at: '2026-03-16T15:00:00',
    },
  ],
  notifications: [
    {
      id: '44444444-4444-4444-8444-444444444444',
      type: 'system',
      content: '林夏补了一条记录，今晚适合看一眼简报。',
      is_read: false,
      created_at: '2026-03-21T09:30:00',
    },
    {
      id: '55555555-5555-4555-8555-555555555555',
      type: 'pair_change',
      content: '顾遥这段关系里有一条移除关系申请，正在等对方决定是否挽留。',
      target_path: '/relationship-space/99999999-9999-4999-8999-999999999999',
      is_read: true,
      created_at: '2026-04-23T10:05:00',
    },
  ],
  todayStatus: {
    pair_id: '22222222-2222-4222-8222-222222222222',
    my_done: true,
    partner_done: true,
    both_done: true,
    has_report: true,
  },
  tree: {
    name: '关系树',
    level: 'tree',
    level_name: '话说开了',
    stage_label: '话说开了',
    stage_title: '原来别着的话，开始能说出来了',
    stage_explanation: '最近的记录里，争执少了，也有了几次日常聊天。',
    growth_points: 148,
    progress_percent: 57,
    next_level_at: 260,
    last_watered: '2026-04-12',
    can_water: true,
    water_bonus: 18,
    decay_per_day: 7,
    decay_grace_days: 0,
    energy_bubbles: [
      { label: '记录', value: '+12' },
      { label: '共情', value: '+8' },
      { label: '缓和', value: '+16' },
    ],
    energy_nodes: [
      { key: 'my_record', label: '记录', points: 10, state: 'available', collected: false, available: true, hint: '领取成长值' },
      { key: 'partner_record', label: '同步', points: 8, state: 'available', collected: false, available: true, hint: '领取成长值' },
      { key: 'small_repair', label: '小行动', points: 12, state: 'available', collected: false, available: true, hint: '领取成长值' },
    ],
    leaves: [
      { label: '聊天记录', value: '12 条', note: '本周保存的聊天内容' },
      { label: '暂停争吵', value: '5 次', note: '争吵时双方同意先暂停' },
      { label: '一起做的事', value: '18 个', note: '一起吃饭、散步等记录' },
    ],
  },
  relationshipSpaces: [
    {
      id: 'couple-repair',
      pair_id: '22222222-2222-4222-8222-222222222222',
      type: '情侣',
      title: '陈一和林夏',
      people: ['陈一', '林夏'],
      tree_stage: '小树',
      status: '今天没有继续争吵',
      prompt: '累的话先休息，晚点再聊。',
      signal: 78,
      moments: ['昨晚加班太累回复短了产生小误会', '今天睡醒各自发了拥抱表情说开了', '今晚约好一起吃饭'],
    },
    {
      id: 'friend-sync',
      pair_id: '77777777-7777-4777-8777-777777777777',
      type: '朋友',
      title: '陈一和周宁',
      people: ['陈一', '周宁'],
      tree_stage: '新芽',
      status: '约好了下次见面的时间',
      prompt: '周总这次放鸽子记账上了，下周烤肉奶茶安排起！',
      signal: 84,
      moments: ['最近各忙各的半个月没碰头', '随手拍了张老粉店照片聊得火热', '约好周六晚上吃火锅'],
    },
    {
      id: 'friend-boundary',
      pair_id: '99999999-9999-4999-8999-999999999999',
      type: '朋友',
      title: '陈一和顾遥',
      people: ['陈一', '顾遥'],
      tree_stage: '种子',
      status: '已经说清各自负责的部分',
      prompt: '我负责的材料写好了，你那部分进度怎么样？今晚一起看一下吧。',
      signal: 69,
      moments: ['项目进度和原计划不一致', '重新确认了分工和交稿时间', '约好周四晚上一起看初稿'],
    },
  ],
  relationshipMetrics: {
    '22222222-2222-4222-8222-222222222222': {
      score: 78,
      trend: 'up',
      summary: '今天把昨天的误会说清楚了。',
      nextAction: '晚上有空时打个电话。',
    },
    '77777777-7777-4777-8777-777777777777': {
      score: 84,
      trend: 'flat',
      summary: '最近见面少，今天聊起了以前常去的店。',
      nextAction: '问问周末在哪吃饭。',
    },
    '99999999-9999-4999-8999-999999999999': {
      score: 69,
      trend: 'up',
      summary: '已经重新确认了分工和交稿时间。',
      nextAction: '今晚一起看一下初稿。',
    },
  },
  crisis: {
    crisis_level: 'moderate',
    health_score: 78,
    intervention: {
      title: '先暂停争吵',
      description: '如果现在说不下去，可以先暂停，约个时间再聊。',
    },
  },
  communityTips: [
    {
      id: 'tip-demo-1',
      title: '先说具体的事',
      description: '说清发生了什么，再说自己的感受和要求。',
      content: '例如：“今天等了很久没收到消息，我有些着急。下次忙的时候能先告诉我一声吗？”',
    },
    {
      id: 'tip-demo-2',
      title: '换个时间再聊',
      description: '双方都愿意时，可以散步时聊，也可以另约时间。',
      content: '先确认对方愿不愿意继续，不必当场解决所有问题。',
    },
  ],
  tasks: {
    daily_note: '今天先选一件有空做的事。',
    daily_pack_label: '今天少安排一些',
    adaptive_strategy: {
      reason: '双方都累了，今天少安排一些。',
      copy_mode: 'gentle',
      copy_feedback_count: 3,
    },
    tasks: [
      {
        id: 'task-demo-1',
        title: '各自休息十分钟',
        description: '先暂停聊天，各自休息十分钟，再决定是否继续。',
        category: 'connection',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'pending',
      },
      {
        id: 'task-demo-2',
        title: '一次只聊一件具体事',
        description: '先说清这次发生的事，不把以前的分歧一起拿出来。',
        category: 'repair',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'pending',
      },
      {
        id: 'task-demo-3',
        title: '记下这次怎么处理的',
        description: '写下这次怎么处理分歧，以及有没有帮助。',
        category: 'reflection',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'completed',
        feedback: {
          usefulness_score: 4,
          friction_score: 2,
          relationship_shift_score: 1,
          note: '各自休息了一会儿，后来把事情说清楚了。',
        },
        needs_feedback: false,
      },
      {
        id: 'task-demo-4',
        title: '睡前打个电话',
        description: '先问对方方不方便，有空就聊几分钟。',
        category: 'connection',
        source: 'manual',
        is_manual: true,
        target_scope: 'self',
        status: 'pending',
      },
    ],
  },
  streak: { streak: 6 },
  latestReport: {
    id: '66666666-6666-4666-8666-666666666666',
    pair_id: '22222222-2222-4222-8222-222222222222',
    report_type: 'daily',
    status: 'completed',
    created_at: '2026-03-21T22:10:00',
    health_score: 78,
    summary: '最近的记录多次提到加班和疲惫，双方也谈过回复消息的事。',
    key_insights: [
      '双方都有主动联系的记录。',
      '关于以后的日子和周末的小计划，两个人步调其实一直挺一致的。',
      '累大发的时候说话语气容易冲，一不小心就会让对方想缩回壳子里。',
    ],
    recommendations: [
      '先问问对方今天想不想聊，不想聊就另约时间。',
      '可以说：“今天一直没等到回复，我有些着急。你方便的时候回我一下吧。”',
      '先聊当前这件事，没说清楚的另找时间继续。',
    ],
  },
  narrativeAlignment: {
    event_id: '99999999-9999-4999-8999-999999999999',
    pair_id: '22222222-2222-4222-8222-222222222222',
    checkin_date: '2026-09-05',
    user_a_label: '陈一',
    user_b_label: '林夏',
    alignment_score: 71,
    shared_story: '你们都在乎这段关系，只是最近一个人在努力确认“我还重要吗”，另一个人在努力证明“我不是不在乎，只是太累了”。',
    view_a_summary: '希望得到及时的回应与在乎，当对方疲惫退开时容易感到失落和不安。',
    view_b_summary: '近期工作高压极度透支，回家更需要放空与安静，把沉默当做避免争吵的降温方式。',
    misread_risk: '最容易错位的点是：追问容易被听成指责和压力，沉默容易被误解为不在乎和退缩。',
    divergence_points: ['一方以为是在确认连接，另一方感受到的是再次被要求汇报交代。', '一方以为沉默是在避免摩擦，另一方感受到的却是被冷落抛下。'],
    bridge_actions: ['进门先倒一杯温水默默陪坐，不追问白天的工作细节。', '留出20分钟放空缓冲期，等呼吸慢下来再聊轻松话题。', '用“我有点想你”代替“你怎么才回我”。'],
    suggested_opening: '今天累不累？想先歇会儿，还是聊一会儿？',
    coach_note: '接住疲惫比解决问题更重要，先对齐“彼此都在乎”这一点。',
    algorithm_version: 'relationship_judgement_v2',
    confidence: 0.74,
    decision_trace: { algorithm_version: 'relationship_judgement_v2', layer: 'alignment' },
    focus_labels: ['回应节奏', '缓冲空间'],
    risk_score: 0.29,
    baseline_delta: 17,
    fallback_reason: null,
    shadow_result: null,
    feedback_status: 'pending_feedback',
    reaction_shift: '林夏：疲惫时更需要安静降温，不喜被追问细节。',
    deviation_reasons: ['近期都在高压期，容易把对方的疲惫误读为冷淡。'],
    history_sufficiency: 'sufficient',
    current_risk_level: 'low',
    active_plan_type: 'companion_soothing_plan',
    generated_at: '2026-03-21T22:15:00',
  },
    messageSimulation: {
    event_id: '88888888-8888-4888-8888-888888888888',
    draft: '你今天怎么又这么晚才回我，我真的很烦。',
    partner_view: '对方可能先注意到责怪的语气，没有理解你在意的是等待消息这件事。',
    likely_impact: '交流可能转向争论语气，而没有说清双方对回复时间的期待。',
    risk_level: 'high',
    risk_reason: '“怎么又”容易让对方觉得被责怪，而原话没有说明希望对方怎样回复。',
    safer_rewrite: '今天等了很久没收到你的消息，我有些烦躁。你方便的时候能回我一下吗？如果暂时没空，也希望你告诉我一声。',
    suggested_tone: '平静、直接',
    conversation_goal: '说清等待消息时的感受和期待',
    do_list: [
      '说清发生了什么，以及自己的感受。',
      '提出具体请求，例如方便时回复一句。',
      '也听听对方对回复时间的想法。',
    ],
    avoid_list: [
      '避免用“每次都这样”概括对方。',
      '不要把一次迟回复说成人品问题。',
      '情绪激动时，可以稍后再决定是否发送。',
    ],
    algorithm_version: 'relationship_judgement_v2',
    confidence: 0.78,
    decision_trace: { algorithm_version: 'relationship_judgement_v2', layer: 'message_simulation' },
    focus_labels: ['回应节奏', '语气缓和'],
    risk_score: 2.3,
    baseline_delta: 1.3,
    fallback_reason: null,
    shadow_result: null,
    feedback_status: 'pending_feedback',
    baseline_match: 'strong_deviation',
    deviation_score: 0.78,
    deviation_reasons: ['这次用了直接表达不满的措辞。', '“怎么又”可能被理解为责怪。'],
    reaction_shift: '对方也可能有其他理解，需要在交流中确认。',
    evidence_summary: ['最近工作压力都比较大，神经都绷得紧紧的。', '容易在疲惫时放大对方的迟回。', '可以把回复时间的期待说得更具体。'],
    limitation_note: '这是表达建议，不能预测对方的实际反应。',
    safety_handoff: '如果双方情绪都很激动，可以先暂停，稍后再沟通。',
  },
  attachmentAnalysis: {
    scope: 'pair',
    analyzed_at: '2026-03-20T20:30:00',
    my_attachment: {
      type: 'anxious',
      label: '焦虑型',
      confidence: 0.81,
      analysis: '记录中几次提到等待回复时感到不安。',
      growth_suggestion: '可以说清自己为什么着急，再问问对方什么时候方便回复。',
    },
    partner_attachment: {
      type: 'avoidant',
      label: '回避型',
      confidence: 0.72,
      analysis: '对方在记录中提到，工作累的时候想先休息。',
      growth_suggestion: '需要休息时可以先说：“我现在有点累，半小时后再聊，可以吗？”',
    },
  },
  repairProtocol: {
    protocol_type: 'structured_repair',
    level: 'moderate',
    title: '吵架后的处理建议',
    summary: '先暂停争论，再看双方是否愿意继续。',
    timing_hint: '先问对方什么时候方便聊。',
    active_plan_type: 'conflict_repair_plan',
    model_family: '亲健陪伴',
    clinical_disclaimer: '本指南用于日常亲密沟通参考，不替代专业心理咨询。',
    focus_tags: ['日常缓和', '说清分歧', '暂停争论'],
    theory_basis: [],
    steps: [
      { sequence: 1, title: '先休息十五分钟', action: '先告诉对方自己需要休息一会儿，再暂停聊天。', why: '避免在气头上脱口而出伤人的狠话。', duration_hint: '10-15 分钟' },
      { sequence: 2, title: '一次只聊一件事', action: '先说刚才哪件事让你介意，不把以前的事一起提出来。', why: '事情越聚焦，越容易说开。', duration_hint: '2 分钟' },
      { sequence: 3, title: '说清感受和要求', action: '可以说：“刚才我还没讲完，你就打断了。我希望你先听我说完。”', why: '说清具体要求，方便双方讨论能不能做到。', duration_hint: '2 分钟' },
      { sequence: 4, title: '确认接下来怎么做', action: '确认双方同意的做法，没有谈妥的可以改天继续。', why: '避免以为说完就代表对方已经同意。', duration_hint: '1 分钟' },
    ],
    do_not: ['千万别连环翻旧账。', '别逼对方在深夜立刻给结论。', '气头上千万不要说散伙的狠话。'],
    success_signal: '双方愿意继续说，也能听完对方的话。',
    escalation_rule: '如果仍然无法继续，可以暂停，另约双方方便的时间。',
    evidence_summary: ['都处在疲惫期，神经容易敏感。', '其实心里都挂念着对方。', '今晚最适合轻柔降温。'],
    limitation_note: '这些建议不一定适合所有情况，由双方决定是否采用。',
    safety_handoff: '要是情绪实在太难受，先抱抱自己，找信得过的朋友倾诉一下。',
  },
  methodology: {
    system_name: '亲健整理方式第一版',
    model_family: '规则判断 + 反馈校准',
    measurement_model: ['每日记录与情绪/互动指标', '安排完成情况', '主观有用度与执行摩擦', '风险等级与健康分趋势'],
    decision_model: ['先看风险层级，再决定是否降温', '根据完成情况和反馈调整分支', '根据当前安排切换提醒和缓和建议'],
    active_modules: ['事件流', '画像快照', '反馈卡片', '当前安排', '冲突缓和建议', '双人安排'],
    current_focus: ['先降温', '再对齐理解', '最后落一个缓和动作'],
    disclaimer: '亲健参考关系心理学和行为科学做整理，不是医学诊断、临床治疗或正式心理测评工具。',
  },
  assessmentPack: {
    title: '关系体检',
    subtitle: '10 题体检。',
    latest_score: 72,
    change_summary: '比上一轮顺一点，继续按现在的节奏来。',
    generated_at: '2026-04-21T09:00:00+08:00',
    items: [
      { item_id: 'anchor-connection-1', track: 'core', dimension: 'connection', dimension_label: '连接与表达', prompt: '这段关系里，我们最近还能把真实想法说出来。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'anchor-connection-2', track: 'core', dimension: 'connection', dimension_label: '连接与表达', prompt: '最近沟通时，我们更像在说同一件事，而不是各说各的。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'anchor-trust-1', track: 'core', dimension: 'trust', dimension_label: '信任与安全', prompt: '最近我大多数时候都能感到被尊重和被认真对待。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
  { item_id: 'anchor-repair-1', track: 'core', dimension: 'repair', dimension_label: '缓和能力', prompt: '有摩擦的时候，我们最近更容易回到同一边。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'anchor-shared-future-1', track: 'core', dimension: 'shared_future', dimension_label: '共同愿景', prompt: '最近我们对这段关系接下来怎么走，仍然有基本共识。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'anchor-vitality-1', track: 'core', dimension: 'vitality', dimension_label: '关系活力', prompt: '最近和对方相处时，我还能感到一点轻松或愉快。', rotation_group: 'anchor', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'rot-trust-1', track: 'rotation', dimension: 'trust', dimension_label: '信任与安全', prompt: '最近我不太需要反复确认自己在这段关系里的位置。', rotation_group: 'trust-a', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'rot-repair-1', track: 'rotation', dimension: 'repair', dimension_label: '缓和能力', prompt: '最近不舒服的时候，我们更容易先把节奏放慢。', rotation_group: 'repair-a', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'rot-shared-future-1', track: 'rotation', dimension: 'shared_future', dimension_label: '共同愿景', prompt: '最近我们对下一步想保留什么关系节奏，越来越清楚。', rotation_group: 'future-a', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
      { item_id: 'rot-vitality-2', track: 'rotation', dimension: 'vitality', dimension_label: '关系活力', prompt: '最近我们相处时，偶尔还能自然地笑出来。', rotation_group: 'vitality-b', active: true, version: 'v1', options: [{ id: 'opt_0', label: '很不符合', score: 0 }, { id: 'opt_25', label: '不太符合', score: 25 }, { id: 'opt_50', label: '一半一半', score: 50 }, { id: 'opt_75', label: '比较符合', score: 75 }, { id: 'opt_100', label: '很符合', score: 100 }] },
    ],
  },
  assessmentLatest: {
    event_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    submitted_at: '2026-04-14T21:00:00',
    total_score: 72,
    scope: 'pair',
    change_summary: '比上一轮顺一点，继续按现在的节奏来。',
    dimension_scores: [
      { id: 'connection', label: '连接与表达', score: 75, status: 'strong' },
      { id: 'trust', label: '信任与安全', score: 62, status: 'watch' },
      { id: 'repair', label: '缓和能力', score: 58, status: 'watch' },
      { id: 'shared_future', label: '共同愿景', score: 76, status: 'strong' },
      { id: 'vitality', label: '关系活力', score: 70, status: 'watch' },
    ],
  },
  assessmentTrend: {
    latest_score: 72,
    change_summary: '比上一轮顺一点，继续按现在的节奏来。',
    dimension_scores: [
      { id: 'connection', label: '连接与表达', score: 75, status: 'strong' },
      { id: 'trust', label: '信任与安全', score: 62, status: 'watch' },
      { id: 'repair', label: '缓和能力', score: 58, status: 'watch' },
      { id: 'shared_future', label: '共同愿景', score: 76, status: 'strong' },
      { id: 'vitality', label: '关系活力', score: 70, status: 'watch' },
    ],
    trend_points: [
      { event_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', submitted_at: '2026-03-24T21:00:00', total_score: 66, scope: 'pair', change_summary: '第一份体检，先留下一个起点。', dimension_scores: [] },
      { event_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', submitted_at: '2026-03-31T21:00:00', total_score: 68, scope: 'pair', change_summary: '比上一轮顺一点，继续按现在的节奏来。', dimension_scores: [] },
      { event_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', submitted_at: '2026-04-07T21:00:00', total_score: 70, scope: 'pair', change_summary: '比上一轮顺一点，继续按现在的节奏来。', dimension_scores: [] },
      { event_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', submitted_at: '2026-04-14T21:00:00', total_score: 72, scope: 'pair', change_summary: '比上一轮顺一点，继续按现在的节奏来。', dimension_scores: [] },
    ],
  },
  reportHistory: [
    { id: '66666666-6666-4666-8666-666666666664', report_type: 'daily', status: 'completed', created_at: '2026-03-19T22:05:00', health_score: 71 },
    { id: '66666666-6666-4666-8666-666666666665', report_type: 'daily', status: 'completed', created_at: '2026-03-20T22:06:00', health_score: 75 },
    { id: '66666666-6666-4666-8666-666666666666', report_type: 'daily', status: 'completed', created_at: '2026-03-21T22:10:00', health_score: 78 },
  ],
  timelineArchive: [
    {
      id: 'archive-demo-1',
      item_type: 'record',
      occurred_at: '2026-03-21T20:40:00',
      local_date: '2026-03-21',
      title: '把心里话悄悄写下来',
      summary: '记录了刚才的分歧，并附了一张两人的合照。',
      tags: ['有点委屈', '盼着和好', '日常碎碎念'],
      visibility: 'owner_only',
      has_raw_content: true,
      has_image_original: true,
      has_voice_original: false,
      raw_retention_until: '2026-03-28T20:40:00',
      raw_deleted_at: null,
      download_available: true,
      record: {
        content: '刚才说话的时候有点委屈，想等晚些时候再把事情说清楚。',
        mood_tags: ['有点委屈', '盼着和好'],
        sentiment_score: 6.8,
        mood_score: 6,
        interaction_freq: 4,
        interaction_initiative: 'me',
        deep_conversation: true,
        task_completed: false,
        image: {
          access_url: null,
          available: true,
          analysis: {
            scene_summary: '一张聊天截图，双方都在试着递台阶把误会解开。',
            mood: '温柔里带着一点脆弱',
          },
        },
        voice: {
          access_url: null,
          available: false,
          duration_seconds: null,
          silence_ratio: null,
        },
        archive_insight: {
          text_emotion: {
            primary_mood: '有点委屈',
            secondary_moods: ['盼着和好'],
            reason: '记录中提到了委屈，也表达了继续沟通的意愿。',
          },
        },
        client_context_preview: {
          intent: 'reflection',
          risk_level: 'watch',
          upload_policy: 'full',
          source_type: 'mixed',
        },
      },
    },
    {
      id: 'archive-demo-2',
      item_type: 'partner_record_placeholder',
      occurred_at: '2026-03-21T21:00:00',
      local_date: '2026-03-21',
      title: '对方悄悄留下的心情印记',
      summary: '对方今晚也提交了一条记录。',
      tags: ['温柔靠近', '心意相通'],
      visibility: 'shared_summary',
      locked_reason: '原文和原媒体默认仅记录者本人可见。',
      has_raw_content: false,
      has_image_original: false,
      has_voice_original: false,
      raw_retention_until: '2026-03-28T21:00:00',
      raw_deleted_at: null,
      download_available: false,
    },
    {
      id: 'archive-demo-3',
      item_type: 'report',
      occurred_at: '2026-03-21T22:10:00',
      local_date: '2026-03-21',
      title: '每日简报',
      summary: '最近双方都提到工作累，回家后不太想说话。',
      tags: ['日常简报', '爱意沉淀'],
      visibility: 'shared_report',
      has_raw_content: false,
      has_image_original: false,
      has_voice_original: false,
      raw_retention_until: null,
      raw_deleted_at: null,
      download_available: true,
      report: {
        report_type: 'daily',
        status: 'completed',
        health_score: 78,
        report_date: '2026-03-21',
        summary: '最近双方都提到工作累，回家后不太想说话。',
        recommendations: [
          '先问问对方今天想不想聊，不想聊就另约时间。',
          '把聊天控制在10分钟以内，互道晚安安心入睡。',
        ],
        content: {
          insight: '最近双方都提到工作累，回家后不太想说话。',
        },
      },
    },
  ],
  timelineEvents: [
    // 林夏（伴侣 22222222-2222-4222-8222-222222222222）
    {
      id: 'timeline-demo-lx-1',
      pair_id: '22222222-2222-4222-8222-222222222222',
      title: '同居分工小调整',
      description: '聊了厨房碗筷分工，一人洗一天，堆在那儿也不催，心情松弛很多。',
      timestamp: '2026-09-01T20:30:00',
      tags: ['生活默契', '家务分工'],
    },
    {
      id: 'timeline-demo-lx-2',
      pair_id: '22222222-2222-4222-8222-222222222222',
      title: '深夜加班留灯倒水',
      description: '林夏加班到十点半，进门时拖鞋摆好、温水放桌上，安静陪着没追问细节。',
      timestamp: '2026-09-03T22:15:00',
      tags: ['贴心陪伴', '情绪支持'],
    },
    {
      id: 'timeline-demo-lx-3',
      pair_id: '22222222-2222-4222-8222-222222222222',
      title: '散步时把误会说透',
      description: '关于周末行程沟通有点摩擦，饭后在楼下公园走了一圈，把各自的担心讲清楚了。',
      timestamp: '2026-09-05T19:40:00',
      tags: ['双视角', '缓和沟通'],
    },
    {
      id: 'timeline-demo-lx-4',
      pair_id: '22222222-2222-4222-8222-222222222222',
      title: '近郊公园草地晒太阳',
      description: '自然醒后去近郊草地发呆喝咖啡，零压力出行，两个人都彻底放松了。',
      timestamp: '2026-09-07T15:20:00',
      tags: ['轻松周末', '自然醒'],
    },

    // 周宁（朋友 77777777-7777-4777-8777-777777777777）
    {
      id: 'timeline-demo-zn-1',
      pair_id: '77777777-7777-4777-8777-777777777777',
      title: '米粉店排队日常问候',
      description: '路过当年常去的那家老粉店，随手拍了张排队照发给周宁，老友搭话自然不尴尬。',
      timestamp: '2026-09-02T12:30:00',
      tags: ['老友问候', '共同回忆'],
    },
    {
      id: 'timeline-demo-zn-2',
      pair_id: '77777777-7777-4777-8777-777777777777',
      title: '周总爽约记在鸽子账本',
      description: '周宁为加班临时鸽了展会，顺势调侃记账，约定周六他请烤肉翻篇。',
      timestamp: '2026-09-04T19:10:00',
      tags: ['损友互怼', '鸽子记账'],
    },
    {
      id: 'timeline-demo-zn-3',
      pair_id: '77777777-7777-4777-8777-777777777777',
      title: '吐槽职场烂人及时止损',
      description: '听周宁疯狂吐槽部门甩锅奇葩，站他这边陪骂了十分钟，适时打住各自早歇。',
      timestamp: '2026-09-06T21:40:00',
      tags: ['情绪排毒', '边界守护'],
    },
    {
      id: 'timeline-demo-zn-4',
      pair_id: '77777777-7777-4777-8777-777777777777',
      title: '顺手结清上月拼车账单',
      description: '查完账顺手微信转了上次拼车钱，老朋友之间有事说事，账目清爽。',
      timestamp: '2026-09-08T11:00:00',
      tags: ['顺手记账', '轻松透明'],
    },

    // 顾遥（搭子 99999999-9999-4999-8999-999999999999）
    {
      id: 'timeline-demo-gy-1',
      pair_id: '99999999-9999-4999-8999-999999999999',
      title: '羽毛球配合战术小复盘',
      description: '局间休息随口复盘，调整为顾遥前场抓网前、我负责后场下压，配合顺畅很多。',
      timestamp: '2026-09-02T20:00:00',
      tags: ['运动搭子', '战术对齐'],
    },
    {
      id: 'timeline-demo-gy-2',
      pair_id: '99999999-9999-4999-8999-999999999999',
      title: '比赛材料交稿前进度对齐',
      description: '距离交稿还有24小时，互相同步进度，明确我搞定前两部分，卡住的地方晚上碰头。',
      timestamp: '2026-09-04T16:30:00',
      tags: ['项目搭子', '进度对齐'],
    },
    {
      id: 'timeline-demo-gy-3',
      pair_id: '99999999-9999-4999-8999-999999999999',
      title: '周末 6 公里休闲徒步拼车',
      description: '约定去走休闲徒步路线，说好随时可撤、不卷步数，大家零负担。',
      timestamp: '2026-09-06T14:10:00',
      tags: ['户外徒步', '零压力'],
    },
    {
      id: 'timeline-demo-gy-4',
      pair_id: '99999999-9999-4999-8999-999999999999',
      title: '群聊话题偏航优雅拉回',
      description: '大家闲聊扯远时自然带回正事，敲定 PPT 最终配色方案，对事不对人。',
      timestamp: '2026-09-07T18:50:00',
      tags: ['高效协作', '对事不对人'],
    },
  ],
  milestones: [
    {
      id: 'milestone-demo-1',
      type: 'anniversary',
      title: '第一次认真复盘',
      date: '2026-02-14',
    },
    {
      id: 'milestone-demo-2',
      type: 'friendship_day',
      title: '陈一和周宁重新约上饭',
      date: '2026-03-16',
    },
    {
      id: 'milestone-demo-3',
      type: 'custom',
      title: '陈一和顾遥第一次一起完成记录',
      date: '2026-03-21',
    },
  ],
  longDistance: {
    health: {
      health_index: 82,
      status: 'stable',
    },
    activities: [
      { id: 'ld-demo-1', activity_type: 'movie', status: 'completed' },
      { id: 'ld-demo-2', activity_type: 'chat', status: 'completed' },
      { id: 'ld-demo-3', activity_type: 'meal', status: 'pending' },
    ],
  },
}

export function cloneDemo(value = demoFixture) {
  return JSON.parse(JSON.stringify(value))
}

const DEMO_ASSESSMENT_PROFILE_COPY = {
  couple: {
    title: '关系体检',
    subtitle: '10 题，看这段关系最该照顾哪里。',
  },
  solo: {
    title: '自我诊断',
    subtitle: '10 题，看你最近最容易卡在哪里。',
  },
  friend: {
    title: '友情体检',
    subtitle: '10 题，看这段友情最该照顾哪里。',
  },
  spouse: {
    title: '婚姻体检',
    subtitle: '10 题，看这段婚姻最该照顾哪里。',
  },
  long_distance: {
    title: '异地关系体检',
    subtitle: '10 题，看异地里最该照顾哪里。',
  },
}

const DEMO_ASSESSMENT_PROMPT_VARIANTS = {
  solo: {
    'anchor-connection-1': '过去一周里，我还能把真正介意的事说出来，不需要一直憋着。',
    'anchor-connection-2': '最近一次重要沟通里，我大致能说清自己到底在介意什么。',
    'anchor-trust-1': '最近大多数时候，我不太需要靠猜测或反复确认，来证明自己在关系里还有位置。',
    'anchor-repair-1': '有摩擦时，我最近至少能先停下来，不把局面越顶越高。',
    'anchor-shared-future-1': '最近我对自己想保留什么样的关系状态，仍然有一点基本认识。',
    'anchor-vitality-1': '最近在关系里，除了压力，我还能感到一点轻松或舒服。',
    'rot-trust-1': '最近我不太需要靠试探、冷一下或反复确认，来判断别人还在不在乎我。',
    'rot-repair-1': '最近有摩擦时，我更能先停 10 分钟，而不是一直追着把话说死。',
    'rot-shared-future-1': '最近我对“这段关系值不值得继续投入”这件事，想法比以前更清楚一点。',
    'rot-vitality-2': '最近在关系里，我偶尔还能自然笑出来，而不只是处理问题。',
  },
  friend: {
    'anchor-connection-1': '过去一周里，这段友情里真正介意的事，我们还能说出来，不需要一直憋着。',
    'anchor-connection-2': '最近一次认真聊天里，我们大致能听懂对方到底在介意什么。',
    'anchor-trust-1': '最近我大多数时候都不用靠猜，能知道自己在这段友情里的位置。',
    'anchor-repair-1': '有别扭时，我们最近至少有一方能先停下来，不把气氛越顶越僵。',
    'anchor-shared-future-1': '最近我们对这段友情接下来怎么相处，仍然有基本共识。',
    'anchor-vitality-1': '最近和这个朋友相处时，除了压力，我还能感到一点轻松或舒服。',
  },
  spouse: {
    'anchor-connection-1': '过去一周里，这段婚姻里真正介意的事，我们还能说出来，不需要一直憋着。',
    'anchor-connection-2': '最近一次重要沟通里，我们大致能听懂对方到底在介意什么，而不是只剩情绪。',
    'anchor-trust-1': '最近我大多数时候都不用靠猜，能知道自己在这段婚姻里的位置。',
    'anchor-repair-1': '有摩擦时，我们最近至少有一方能先停下来，不把家里的气氛越顶越高。',
    'anchor-shared-future-1': '最近我们对这段婚姻接下来怎么走，仍然有基本共识。',
    'anchor-vitality-1': '最近和对方待在一起时，除了现实压力，我还能感到一点轻松或舒服。',
  },
  long_distance: {
    'anchor-connection-1': '过去一周里，隔着距离时真正介意的事，我们还能说出来，不需要一直憋着。',
    'anchor-connection-2': '最近一次重要联系里，我们大致能听懂对方到底在介意什么。',
    'anchor-trust-1': '最近我大多数时候都不用靠猜，能知道自己在这段异地关系里的位置。',
    'anchor-repair-1': '有摩擦时，我们最近至少有一方能先停下来，不把隔着距离的误会越顶越高。',
    'anchor-shared-future-1': '最近我们对这段异地关系接下来怎么走，仍然有基本共识。',
    'anchor-vitality-1': '最近隔着距离联系时，除了压力，我还能感到一点轻松或被陪到。',
  },
}

function demoAssessmentProfileForPair(pair = null) {
  if (pair === 'solo') return 'solo'
  if (!pair) return 'couple'
  if (pair.is_long_distance && ['couple', 'spouse'].includes(pair.type)) return 'long_distance'
  if (['friend', 'bestfriend'].includes(pair.type)) return 'friend'
  if (['spouse', 'parent'].includes(pair.type)) return 'spouse'
  return 'couple'
}

export function buildDemoAssessmentPack(pair = null) {
  const pack = cloneDemo(demoFixture.assessmentPack)
  const profile = demoAssessmentProfileForPair(pair)
  const profileCopy = DEMO_ASSESSMENT_PROFILE_COPY[profile] || DEMO_ASSESSMENT_PROFILE_COPY.couple
  const promptVariants = DEMO_ASSESSMENT_PROMPT_VARIANTS[profile] || {}

  pack.title = profileCopy.title
  pack.subtitle = profileCopy.subtitle
  pack.items = (pack.items || []).map((item) => ({
    ...item,
    prompt: promptVariants[item.item_id] || item.prompt,
  }))

  return pack
}
export const DEMO_PERSONA_QA = {
  "22222222-2222-4222-8222-222222222222": {
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "林夏",
    "roleLabel": "伴侣",
    "relationType": "couple",
    "avatar": "林",
    "themeColor": "#d76848",
    "scenarioDescription": "同居伴侣 · 加班疲惫照顾与情绪支持",
    "initialMessages": [
      {
        "id": "msg-demo-lx-1",
        "role": "user",
        "content": "林夏最近加班特别多，回家后经常叹气，我想关心但又怕说错话让她觉得更烦，怎么开口比较好？",
        "created_at": "2026-09-07T14:00:00"
      },
      {
        "id": "msg-demo-lx-2",
        "role": "assistant",
        "content": "可以先问她：“今天想聊聊，还是先休息？”她愿意说就听，不想说也不用追问。",
        "created_at": "2026-09-07T14:00:15",
        "payload": {
          "task_proposals": [
            {
              "id": "task-demo-lx-1",
              "title": "准备温水与水果，提供低压陪伴",
              "description": "今晚林夏到家后不急着问工作，先递温水并留出 20 分钟安静时间",
              "action_type": "care",
              "duration_minutes": 20,
              "reason": "缓解伴侣一天的高压紧绷，建立被包容的安全感"
            }
          ]
        }
      }
    ],
    "suggestedQuestions": [
      "林夏最近加班经常叹气，怎么关心才不会显得像说教或追问？",
      "我们最近因为谁洗碗和倒垃圾有点摩擦，怎么沟通分工更顺畅？",
      "周末想带林夏去近郊放松，怎么提议能让她不感到行程压力？",
      "晚上林夏想聊工作烦心事，我除了听还能怎么给她有效支持？"
    ],
    "replies": {
      "林夏最近加班经常叹气，怎么关心才不会显得像说教或追问？": "可以问：“今天累不累？想先休息还是聊一会儿？”别预先认定她需要哪种照顾，听听她怎么说。",
      "我们最近因为谁洗碗和倒垃圾有点摩擦，怎么沟通分工更顺畅？": "找双方都有空的时候，把要做的家务列出来。可以说：“最近洗碗和倒垃圾总没分好，咱们重新商量一下怎么分？”",
      "周末想带林夏去近郊放松，怎么提议能让她不感到行程压力？": "可以说：“周六想不想去附近公园走走？不想出门的话就在家休息。”",
      "晚上林夏想聊工作烦心事，我除了听还能怎么给她有效支持？": "先听她说完，再问：“你想让我帮忙想办法，还是就想说说？”不用急着评价她的同事，也不必马上给建议。"
    },
    "defaultReply": "先问问对方现在愿不愿意聊，再说你想谈的具体事情。"
  },
  "77777777-7777-4777-8777-777777777777": {
    "id": "77777777-7777-4777-8777-777777777777",
    "name": "周宁",
    "roleLabel": "朋友",
    "relationType": "friend",
    "avatar": "周",
    "themeColor": "#4d72b0",
    "scenarioDescription": "多年好友 · 约饭出游与爽约调侃边界",
    "initialMessages": [
      {
        "id": "msg-demo-zn-1",
        "role": "user",
        "content": "周宁之前答应一起看展览后来加班爽约了，怎么调侃又不伤感情地回应？",
        "created_at": "2026-09-07T14:05:00"
      },
      {
        "id": "msg-demo-zn-2",
        "role": "assistant",
        "content": "可以说：“那这次先算了，下周有空再约。到时候提前跟我说一声。”如果你确实介意，也可以直接说明，没必要强行开玩笑。",
        "created_at": "2026-09-07T14:05:18",
        "payload": {
          "task_proposals": [
            {
              "id": "task-demo-zn-1",
              "title": "约老友下周补聚餐",
              "description": "下周五前挑一家环境轻松的餐厅，和周宁补一顿周末聚会",
              "action_type": "social",
              "duration_minutes": 90,
              "reason": "及时修补小爽约带来的距离感，维系长期高质量友情"
            }
          ]
        }
      }
    ],
    "suggestedQuestions": [
      "周宁之前答应一起看展览后来加班爽约了，怎么调侃又不伤感情地回应？",
      "好久没联系的朋友，突然想问候一下，怎么发消息不尴尬？",
      "朋友借了我一笔小钱很久没提还，怎么委婉提醒？",
      "朋友向我疯狂吐槽他的同事，我听得很累，怎么体面结束话题？"
    ],
    "replies": {
      "周宁之前答应一起看展览后来加班爽约了，怎么调侃又不伤感情地回应？": "可以回：“行，那你先忙。下次要是来不了，提前跟我说一声就好。”",
      "好久没联系的朋友，突然想问候一下，怎么发消息不尴尬？": "可以发：“好久没聊了，最近怎么样？哪天有空出来吃个饭？”",
      "朋友借了我一笔小钱很久没提还，怎么委婉提醒？": "直接提醒就行：“上次借你的钱，方便这两天还我吗？”不需要编造自己急用钱的理由。",
      "朋友向我疯狂吐槽他的同事，我听得很累，怎么体面结束话题？": "可以说：“我知道这件事让你很烦，不过我现在有些累，今天先聊到这儿吧。”"
    },
    "defaultReply": "有事直接说，不确定对方是否介意的玩笑就先别开。"
  },
  "99999999-9999-4999-8999-999999999999": {
    "id": "99999999-9999-4999-8999-999999999999",
    "name": "顾遥",
    "roleLabel": "搭子",
    "relationType": "friend",
    "avatar": "顾",
    "themeColor": "#3a8877",
    "scenarioDescription": "羽毛球搭子 · 项目组队搭档 · 催进度边界",
    "initialMessages": [
      {
        "id": "msg-demo-gy-1",
        "role": "user",
        "content": "我和顾遥一起组队做比赛项目，分工好的一份调研报告周五要交，但他到现在还没动静。我们只是项目搭子，关系不算特别铁，怎么催进度才显得职业又直接？",
        "created_at": "2026-09-07T14:10:00"
      },
      {
        "id": "msg-demo-gy-2",
        "role": "assistant",
        "content": "可以说：“顾遥，我负责的部分写好了，你那边进度怎么样？今晚一起看一下初稿吧。”",
        "created_at": "2026-09-07T14:10:20",
        "payload": {
          "task_proposals": [
            {
              "id": "task-demo-gy-1",
              "title": "同步项目材料初稿并锁定节点",
              "description": "周四晚 20:00 前在线对齐用户调研模块合并版",
              "action_type": "align",
              "duration_minutes": 15,
              "reason": "保证周五准时提交，避免责任推诿与最后关头手忙脚乱"
            }
          ]
        }
      }
    ],
    "suggestedQuestions": [
      "组队比赛/项目分工时对方进度有点慢，怎么直接而不失礼貌地对齐进度？",
      "作为运动搭子，想商量改变打球配合战术，怎么沟通更自然？",
      "想约搭子周末一起去户外徒步，怎么给出轻松无负担的选择？",
      "搭子在群里发了不太合适的话题，怎么不失尴尬地把话题拉回来？"
    ],
    "replies": {
      "组队比赛/项目分工时对方进度有点慢，怎么直接而不失礼貌地对齐进度？": "可以说：“快到提交时间了，你那部分还差哪些？我们一起看看剩下的怎么分。”",
      "作为运动搭子，想商量改变打球配合战术，怎么沟通更自然？": "可以说：“下一局换一下站位试试？你在前面，我守后场，看看配合怎么样。”",
      "想约搭子周末一起去户外徒步，怎么给出轻松无负担的选择？": "可以发：“周六打算去徒步，大概六公里，你有空一起吗？”",
      "搭子在群里发了不太合适的话题，怎么不失尴尬地把话题拉回来？": "可以说：“这个先不聊了，我们继续看报告第三部分吧。”"
    },
    "defaultReply": "把要一起做的事、时间和分工说清楚，有变化及时告诉对方。"
  }
}

export function listDemoPersonas() {
  return Object.values(DEMO_PERSONA_QA)
}

export function getDemoPersonaQA(pairId = null) {
  const fallbackKey = '22222222-2222-4222-8222-222222222222'
  if (!pairId) return DEMO_PERSONA_QA[fallbackKey]
  return DEMO_PERSONA_QA[pairId] || DEMO_PERSONA_QA[fallbackKey]
}

export function getDemoPersonaReply(pairId, question) {
  const persona = getDemoPersonaQA(pairId)
  const trimmed = String(question || '').trim()
  if (persona.replies && persona.replies[trimmed]) {
    return persona.replies[trimmed]
  }
  for (const [key, reply] of Object.entries(persona.replies || {})) {
    if (trimmed.includes(key) || key.includes(trimmed)) {
      return reply
    }
  }
  return persona.defaultReply
}

export const DEMO_NARRATIVE_ALIGNMENTS = {
  '22222222-2222-4222-8222-222222222222': {
    event_id: '99999999-9999-4999-8999-999999999999',
    pair_id: '22222222-2222-4222-8222-222222222222',
    checkin_date: '2026-09-05',
    user_a_label: '陈一',
    user_b_label: '林夏',
    alignment_score: 71,
    shared_story: '你们都在乎这段关系，只是最近一个人在努力确认“我还重要吗”，另一个人在努力证明“我不是不在乎，只是太累了”。',
    view_a_summary: '希望得到及时的回应与在乎，当对方疲惫退开时容易感到失落和不安。',
    view_b_summary: '近期工作高压极度透支，回家更需要放空与安静，把沉默当做避免争吵的降温方式。',
    misread_risk: '最容易错位的点是：追问容易被听成指责和压力，沉默容易被误解为不在乎和退缩。',
    divergence_points: ['一方以为是在确认连接，另一方感受到的是再次被要求汇报交代。', '一方以为沉默是在避免摩擦，另一方感受到的却是被冷落抛下。'],
    bridge_actions: ['进门先倒一杯温水默默陪坐，不追问白天的工作细节。', '留出20分钟放空缓冲期，等呼吸慢下来再聊轻松话题。', '用“我有点想你”代替“你怎么才回我”。'],
    suggested_opening: '今天累不累？想先歇会儿，还是聊一会儿？',
    coach_note: '接住疲惫比解决问题更重要，先对齐“彼此都在乎”这一点。',
    reaction_shift: '林夏：疲惫时更需要安静降温，不喜被追问细节。',
    deviation_reasons: ['近期都在高压期，容易把对方的疲惫误读为冷淡。'],
    history_sufficiency: 'sufficient',
    current_risk_level: 'low',
    active_plan_type: 'companion_soothing_plan',
  },
  '77777777-7777-4777-8777-777777777777': {
    event_id: 'a7777777-7777-4777-8777-777777777777',
    pair_id: '77777777-7777-4777-8777-777777777777',
    checkin_date: '2026-09-05',
    user_a_label: '陈一',
    user_b_label: '周宁',
    alignment_score: 85,
    shared_story: '多年老友习惯互损开玩笑，这次看展爽约并不是感情变淡，而是突发加班导致精力耗尽。',
    view_a_summary: '本来挺期待周末一起聚聚看展，临时被放鸽子有点落空，但又不好意思太正经地催。',
    view_b_summary: '临时代班焦头烂额，觉得老朋友应该能懂自己的身不由己，心里其实挺过意不去的。',
    misread_risk: '都想维持老朋友之间“不端着”的轻松感，反而可能因为没直接把下次约好而悬在半空。',
    divergence_points: ['一方担心老朋友各忙各的联系变少。', '另一方在忙碌中感到歉疚却不知如何破冰补偿。'],
    bridge_actions: ['直接半开玩笑地把这笔账记在奶茶上，把尴尬化解成下次聚会的由头。', '周四前主动锁定一个下周吃顿饭的时间。'],
    suggested_opening: '那这次就算了，下周有空再约吧。',
    coach_note: '老朋友之间损着损着就把下次约好了，不用搞得很沉重。',
    reaction_shift: '周宁：工作忙碌但重视友情，开得起玩笑。',
    deviation_reasons: ['工作突发变动，无恶意爽约。'],
    history_sufficiency: 'sufficient',
    current_risk_level: 'low',
    active_plan_type: 'friendship_reconnect_plan',
  },
  '99999999-9999-4999-8999-999999999999': {
    event_id: 'a9999999-9999-4999-8999-999999999999',
    pair_id: '99999999-9999-4999-8999-999999999999',
    checkin_date: '2026-09-05',
    user_a_label: '陈一',
    user_b_label: '顾遥',
    alignment_score: 79,
    shared_story: '搭子协作目标高度一致，只是做事节奏有差异：一方习惯提前分段对齐，另一方习惯临近截止冲刺交付。',
    view_a_summary: '希望清楚知道整体进度条到哪了，看不到中间进展会担心周五交差时手忙脚乱。',
    view_b_summary: '习惯集中精力独立憋大招，觉得只要最后能交出好东西就行，没意识到需要同步中间态。',
    misread_risk: '催进度容易被听成不信任对方能力，不催又容易变成单方面焦虑。',
    divergence_points: ['过程透明感与深度专注之间的权衡。'],
    bridge_actions: ['对事不对人，约定今晚 15 分钟快速过一下初稿框架。', '明确提出我能分担哪一部分，而不是单纯催交。'],
    suggested_opening: '遥遥，周五要交的材料我这块弄好了。你调研部分到哪步了？卡壳的随时扔给我，今晚咱们合一下初稿。',
    coach_note: '搭子关系最舒适的就是界限清楚、有事说事、高效协作。',
    reaction_shift: '顾遥：重视交付质量，适合直接对齐分工。',
    deviation_reasons: ['协作节奏差异，对齐预期即可化解。'],
    history_sufficiency: 'sufficient',
    current_risk_level: 'low',
    active_plan_type: 'task_alignment_plan',
  }
}
demoFixture.narrativeAlignments = DEMO_NARRATIVE_ALIGNMENTS

export function getDemoNarrativeAlignment(pairId = null) {
  const fallbackKey = '22222222-2222-4222-8222-222222222222'
  if (!pairId) return DEMO_NARRATIVE_ALIGNMENTS[fallbackKey]
  return DEMO_NARRATIVE_ALIGNMENTS[pairId] || DEMO_NARRATIVE_ALIGNMENTS[fallbackKey]
}

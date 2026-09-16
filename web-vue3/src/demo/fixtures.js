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
    stage_explanation: '最近气氛明显缓和多啦，以前容易别扭的小话，现在能笑着用平常心说出来啦~',
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
      { key: 'my_record', label: '记录', points: 10, state: 'available', collected: false, available: true, hint: '点击抓取成长值' },
      { key: 'partner_record', label: '同步', points: 8, state: 'available', collected: false, available: true, hint: '点击抓取成长值' },
      { key: 'small_repair', label: '小行动', points: 12, state: 'available', collected: false, available: true, hint: '点击抓取成长值' },
    ],
    leaves: [
      { label: '走心原话', value: '12 条', note: '这周被温柔接住的关键真心话' },
      { label: '默契刹车', value: '5 次', note: '气氛刚要僵住时成功软化化解' },
      { label: '闪光小日常', value: '18 个', note: '一起喝奶茶、散步发呆的甜甜瞬间' },
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
      status: '今天适合安安静静的温柔陪伴~',
      prompt: '工作累了一天辛苦啦，回家先好好歇着，有我在呢~',
      signal: 78,
      moments: ['昨晚加班太累回复短了产生小误会', '今天睡醒各自发了拥抱表情说开了', '今晚决定一起吃顿热乎饭放松~'],
    },
    {
      id: 'friend-sync',
      pair_id: '77777777-7777-4777-8777-777777777777',
      type: '朋友',
      title: '陈一和周宁',
      people: ['陈一', '周宁'],
      tree_stage: '新芽',
      status: '老友之间损着损着就把下次约好了~',
      prompt: '周总这次放鸽子记账上了，下周烤肉奶茶安排起！',
      signal: 84,
      moments: ['最近各忙各的半个月没碰头', '随手拍了张老粉店照片聊得火热', '敲定了周六晚一起出来涮火锅~'],
    },
    {
      id: 'friend-boundary',
      pair_id: '99999999-9999-4999-8999-999999999999',
      type: '朋友',
      title: '陈一和顾遥',
      people: ['陈一', '顾遥'],
      tree_stage: '种子',
      status: '搭子关系有事说事、界限清楚最舒服~',
      prompt: '周五要交的材料我弄好了，你卡住的随时扔给我，今晚对一下初稿~',
      signal: 69,
      moments: ['组队做项目节奏不同步有点小卡壳', '坦诚对齐各自负责的模块和交稿节点', '约定周四晚 15 分钟快速过初稿~'],
    },
  ],
  relationshipMetrics: {
    '22222222-2222-4222-8222-222222222222': {
      score: 78,
      trend: 'up',
      summary: '今天彼此都递了暖心台阶，气氛正在迅速回暖呢~',
      nextAction: '晚上打个5分钟轻松电话，互道一句晚安~',
    },
    '77777777-7777-4777-8777-777777777777': {
      score: 84,
      trend: 'flat',
      summary: '友情基底很扎实，虽然忙得少见，但一聊起来还是那么亲切~',
      nextAction: '发个搞怪表情包，把周末的饭局敲死~',
    },
    '99999999-9999-4999-8999-999999999999': {
      score: 69,
      trend: 'up',
      summary: '协作步调正在渐渐磨合顺畅，目标很明确~',
      nextAction: '今晚花10分钟对一下初稿进度，轻松搞定它~',
    },
  },
  crisis: {
    crisis_level: 'moderate',
    health_score: 78,
    intervention: {
      title: '别慌，先深呼吸给彼此降个温~',
      description: '气头上先别急着争对错，今晚先吃好睡饱，天大的事等心平气和再聊。',
    },
  },
  communityTips: [
    {
      id: 'tip-demo-1',
      title: '软软的开场白最管用',
      description: '试着把“你又干嘛”换成“今天累坏了吧”，对方就算浑身是刺也会瞬间卸下防备~',
      content: '当对方情绪激动时，你先递过去一个台阶，语气软一度，争吵的概率就降低八成。',
    },
    {
      id: 'tip-demo-2',
      title: '散步是最好的破冰药',
      description: '别在封闭压抑的屋里对坐谈判，并排在路灯下慢慢走，很多憋着的话自然就说开了~',
      content: '并排走路时没有眼神对视的压迫感，身体在走动，情绪也会跟着流动起来。',
    },
  ],
  tasks: {
    daily_note: '今天挑两三件最轻巧、没负担的小事，慢慢找回舒服的节奏~',
    daily_pack_label: '今天先放轻松点~',
    adaptive_strategy: {
      reason: '先给心情顺顺毛，再一起做件暖暖的小事~',
      copy_mode: 'gentle',
      copy_feedback_count: 3,
    },
    tasks: [
      {
        id: 'task-demo-1',
        title: '先给彼此留 10 分钟空白',
        description: '累的时候别急着争对错，各自倒杯水、深呼吸放空 10 分钟~',
        category: 'connection',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'pending',
      },
      {
        id: 'task-demo-2',
        title: '一次只聊一件具体事',
        description: '就事论事最轻松，千万别顺带翻以前的小账本呀~',
        category: 'repair',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'pending',
      },
      {
        id: 'task-demo-3',
        title: '踩一脚刹车总结',
        description: '做完后留一句体己话，下次气氛有点冲时知道怎么抱抱对方~',
        category: 'reflection',
        source: 'system',
        is_manual: false,
        target_scope: 'both',
        status: 'completed',
        feedback: {
          usefulness_score: 4,
          friction_score: 2,
          relationship_shift_score: 1,
          note: '试了一下先各自静静，果然谁也没吵起来，气氛很快就软下来了~',
        },
        needs_feedback: false,
      },
      {
        id: 'task-demo-4',
        title: '睡前打个5分钟轻松电话',
        description: '不用聊大道理，就互道一句晚安、听听对方声音，安心睡个好觉~',
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
    summary: '其实你们心里都有彼此，只是这几天工作生活压力都顶在头上，一回家都累瘫了，想好好说句话都容易变成叹气~',
    key_insights: [
      '虽然都累得够呛，但谁也没真撂挑子，心里还在惦记着对方呢~',
      '关于以后的日子和周末的小计划，两个人步调其实一直挺一致的。',
      '累大发的时候说话语气容易冲，一不小心就会让对方想缩回壳子里。',
    ],
    recommendations: [
      '今晚别聊严肃大话题啦，倒杯温水、切盘水果，安安静静待会儿就好~',
      '试着把“你怎么又这样”换成“我今天有点想你，没回我有点失落呢~”，对方听了心会软下来。',
      '有事说事不翻旧账，先把今晚的饭吃美、觉睡饱，小事明天自然就顺啦~',
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
    suggested_opening: '夏夏，今天辛苦啦。先瘫会儿歇着，不想说话就先不聊，等会儿饿了我给你热点吃的~',
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
    partner_view: '对方一看到很可能先觉得是在被劈头盖脸责怪，下意识就想关掉对话框防守反击啦~',
    likely_impact: '直接发出去的话，大概率会换来冷冰冰的借口或者干脆已读不回，原本想被哄一下反而变成生闷气~',
    risk_level: 'high',
    risk_reason: '“怎么又”三个字杀伤力太强啦，把心里的思念和委屈一下全包装成了火药味，对方听不到你的软肋只会感受到被怼~',
    safer_rewrite: '知道你今天肯定忙得团团转，没顾上看手机也正常。只是我这边一直等不到你的消息，心里有点空落落的，挺挂念你的。你先安心忙，忙完随手回我个小表情就好，我等你~',
    suggested_tone: '温柔轻软·先体谅再示弱',
    conversation_goal: '让对方心软并愿意主动回应',
    do_list: [
      '先垫一句体谅对方辛苦，把心里的在乎与挂念软软说出来~',
      '给对方一个随手能回复的低压小台阶（比如报个平安或丢个小表情）~',
      '目的是让对方心疼你、想来抱抱你，而不是非要争出谁对谁错。',
    ],
    avoid_list: [
      '千万别发泄说“我很烦”或用“你怎么又……”这种扫射式句式啦~',
      '不要把“我需要你”扭曲成“你很差劲”。',
      '气头上千万别发连珠炮小作文，字数越多防卫心越重。',
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
    deviation_reasons: ['今天心里有点憋屈，语气比平时冲了一点点~', '稍微带了点火药味，对方容易误以为要吵架呢'],
    reaction_shift: '对方可能会下意识防卫，先关掉心门。',
    evidence_summary: ['最近工作压力都比较大，神经都绷得紧紧的。', '容易在疲惫时放大对方的迟回。', '换个软一点的方式说，对方更容易心软~'],
    limitation_note: '发前悄悄支招，仅供参考哈~',
    safety_handoff: '要是俩人都还在气头上，先深呼吸喝口水，晚点再发~',
  },
  attachmentAnalysis: {
    scope: 'pair',
    analyzed_at: '2026-03-20T20:30:00',
    my_attachment: {
      type: 'anxious',
      label: '焦虑型',
      confidence: 0.81,
      analysis: '特别在意回复快不快，一旦安静下来就容易胡思乱想，忍不住想反复确认对方还在不在乎~',
      growth_suggestion: '试着把心里的委屈和担心直接说成软软的小请求，不用急着当下就要答案~',
    },
    partner_attachment: {
      type: 'avoidant',
      label: '回避型',
      confidence: 0.72,
      analysis: '压力一上来就想先缩回自己的安全小壳子里，不是冷淡，是真的一点社交电量都没有啦~',
      growth_suggestion: '提前跟对方说一句“我现在脑子好乱，先瘫半小时再找你呀”，会给彼此满满的安全感~',
    },
  },
  repairProtocol: {
    protocol_type: 'structured_repair',
    level: 'moderate',
    title: '让气氛先软下来的急救指南',
    summary: '先让彼此呼吸慢下来，再轻轻递个台阶~',
    timing_hint: '先发一条暖暖的消息垫个底，再打个 5 分钟暖心短通话~',
    active_plan_type: 'conflict_repair_plan',
    model_family: '亲健陪伴',
    clinical_disclaimer: '本指南用于日常亲密沟通参考，不替代专业心理咨询。',
    focus_tags: ['日常缓和', '递个台阶', '温柔降温'],
    theory_basis: [],
    steps: [
      { sequence: 1, title: '先按暂停键 15 分钟', action: '先不急着回消息或追问，倒杯温水、深呼吸几下，让心跳先慢下来~', why: '避免在气头上脱口而出伤人的狠话。', duration_hint: '10-15 分钟' },
      { sequence: 2, title: '一次只解决一个小结巴', action: '先聊刚刚最让你介意的那一处，千万别顺手把以前的憋屈一起倒出来呀~', why: '事情越聚焦，越容易说开。', duration_hint: '2 分钟' },
      { sequence: 3, title: '说软话、提小要求', action: '试着说“我刚才有点失落，抱抱我好不好”，把心里的软肉露出来。', why: '对方听到的是你的脆弱和需要，而不是火药味。', duration_hint: '2 分钟' },
      { sequence: 4, title: '做个温馨小收尾', action: '今晚达成一个小默契就够啦，比如睡前互道一句晚安~', why: '让爱意和温度留在今晚的结尾。', duration_hint: '1 分钟' },
    ],
    do_not: ['千万别连环翻旧账。', '别逼对方在深夜立刻给结论。', '气头上千万不要说散伙的狠话。'],
    success_signal: '彼此语气变软了，愿意继续聊日常。',
    escalation_rule: '如果双方情绪依然很激动，先各自睡个好觉，明天吃饱了再聊~',
    evidence_summary: ['都处在疲惫期，神经容易敏感。', '其实心里都挂念着对方。', '今晚最适合轻柔降温。'],
    limitation_note: '沟通急救参考，怎么舒服怎么来~',
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
      summary: '写下了刚才那点小憋屈，但心里其实还是盼着能和好如初~ 配了一张两个人以前的甜甜合影。',
      tags: ['有点委屈', '盼着和好', '日常碎碎念'],
      visibility: 'owner_only',
      has_raw_content: true,
      has_image_original: true,
      has_voice_original: false,
      raw_retention_until: '2026-03-28T20:40:00',
      raw_deleted_at: null,
      download_available: true,
      record: {
        content: '刚才没忍住叹了口气，心里其实有点小委屈，但转念想想谁都有累的时候，还是想好好跟他说开呀~',
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
            reason: '文字里带着一点点委屈，但更多的是对彼此的珍惜和期待呀~',
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
      summary: '对方今晚也写下了走心的一笔，字里行间卸下了防备，想和你好好的。',
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
      title: '每日暖心简报',
      summary: '其实你们心里都有彼此，只是这几天工作压力大，一回家累瘫了才容易叹气~',
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
        summary: '其实你们心里都有彼此，只是这几天工作压力大，一回家累瘫了才容易叹气~',
        recommendations: [
          '今晚别聊严肃大话题啦，倒杯温水、切盘水果，安安静静待会儿就好~',
          '把聊天控制在10分钟以内，互道晚安安心入睡。',
        ],
        content: {
          insight: '其实你们心里都有彼此，只是这几天工作压力大，一回家累瘫了才容易叹气~',
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
        "content": "放宽心啦~ 回来累趴的人最不需要的就是连环追问啦。你做个暖心小动作就超棒了——她进门的时候，先把拖鞋摆到门口，倒杯温水放手边。等她坐下来轻轻说一句：\"今天累坏了吧~ 冰箱有热汤，先瘫会儿缓缓，不想说话咱就安安静静待着，想骂老板我随时陪你骂~\"\n\n不用刻意找话聊，让她知道家里有你在、踏踏实实的就好啦~",
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
      "林夏最近加班经常叹气，怎么关心才不会显得像说教或追问？": "别问她\"怎么了\"\"工作还好吗\"啦，这种问题一听就要打起精神汇报，累上加累呢~ \n\n你就做一件贴心小事：进门前把拖鞋摆好，倒杯温温的水。等她换好鞋瘫下，跟她说：\"饿不饿呀？给你热个饭，不想说话就先歇着~\" \n\n等她自己缓过劲儿想聊了，自然会找你的啦~",
      "我们最近因为谁洗碗和倒垃圾有点摩擦，怎么沟通分工更顺畅？": "千万别在俩人都累得不行的时候谈家务呀~ 挑个周末吃饱喝足、心情美滋滋的时候聊：\n\n\"夏夏~ 最近咱俩都忙飞了，水槽堆着碗看着怪堵心的。要不咱各包一半？我负责做饭倒垃圾，你负责洗碗，或者按你觉得舒服的来~ 实在懒了咱就叫个保洁，几杯奶茶钱换个清静多划算呀！\"\n\n重点是一起把繁琐家务搞定，别对抗彼此嘛~",
      "周末想带林夏去近郊放松，怎么提议能让她不感到行程压力？": "直接这么提就好啦：\n\n\"夏夏~ 周六天气超级好，附近有个公园很惬意，下午去草地上晒晒太阳、喝杯咖啡发发呆~ 睡到自然醒再出发，不想动了随时打道回府，零压力！\"\n\n关键词就是：睡饱、松弛、随时可撤~ 听着就完全没负担呢~",
      "晚上林夏想聊工作烦心事，我除了听还能怎么给她有效支持？": "先无脑站她这边就对了！她吐槽同事，你就接：\"这也太离谱了吧？！换我也得炸毛！\"\n\n等她吐槽痛快了、气顺过来了，再柔柔问一句：\"要不要我帮你想个损招治治他们？还是就单纯想痛快骂一骂呀？\"\n\n听她的节奏来就好啦~ 别一上来就给人上课讲大道理嘛！"
    },
    "defaultReply": "两个人在一起呀，有时候最管用的不是滔滔不绝，而是默默递过来的一杯温水~ 先接住对方的情绪，比急着解决问题管用多啦！"
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
        "content": "哈哈这种事直接损他就好啦，老铁之间哪用端着呀：\n\n\"周总果然贵人事忙呀~ 放鸽子的小账本我可给你狠狠记上一笔啦！下周必须补我一顿大餐，地方你挑但奶茶得你包，这事就算翻篇啦~ 忙完赶紧早点躺平，别熬头秃了哈！\"\n\n既给了台阶又把下次饭局敲定了，美滋滋~",
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
      "周宁之前答应一起看展览后来加班爽约了，怎么调侃又不伤感情地回应？": "直接发：\"行吧周总，为国家 GDP 贡献力量辛苦啦~ 这次先记账上，下次必须你请客而且不许迟到，就这么定啦！忙完赶紧歇着别硬熬哈~\"\n\n老友之间互损几句，既亲切又把下次约好啦！",
      "好久没联系的朋友，突然想问候一下，怎么发消息不尴尬？": "千万别发干巴巴的\"在吗\"，别人还以为你要结婚随礼呢哈哈！找个共同回忆随口聊：\n\n\"宁子！今天路过咱以前常吃的那家螺蛳粉店，居然还在大排长龙，瞬间想起大学那会儿啦！最近过得怎么样呀？改天出来坐坐呗~\"\n\n超级自然，对方回消息也完全没压力~",
      "朋友借了我一笔小钱很久没提还，怎么委婉提醒？": "找个客观由头，别搞得像审讯催债似的：\n\n\"宁子~ 今天刚还完花呗顺手对账，突然看到上个月那 500 块还在我小账本上挂着呢~ 手头如果方便的话顺手转我一下哈，谢啦兄弟！\"\n\n当成日常随手结账，大家都体体面面的~",
      "朋友向我疯狂吐槽他的同事，我听得很累，怎么体面结束话题？": "先共情一句接住话头：\"天呐摊上这种奇葩同事确实太心塞了！\"\n\n接着找个正当由头优雅撤退：\"不过我手头刚好来了个紧急事要处理，你先吨吨喝口水消消气，别让烂人毁了今晚好心情呀~ 等回头闲了咱再痛快聊！\"\n\n保护好自己的社交电量，完全不用愧疚哈~"
    },
    "defaultReply": "老朋友相处最讲究松弛感啦~ 有事说事，开得起玩笑也守得住底线，怎么舒服怎么来~"
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
        "content": "搭子之间干脆利落最舒服啦，不用兜圈子：\n\n\"顾遥，跟你对一下进度哈——周五交的那份材料，我负责的架构和前言已经搞定啦。你那块用户调研目前进展如何呀？要是有卡点随时丢给我分担点，咱们今晚合一下，争取明晚顺出初稿呀~\"\n\n对事不对人，清爽高效还不失友好~",
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
      "组队比赛/项目分工时对方进度有点慢，怎么直接而不失礼貌地对齐进度？": "直接这么说超得体：\"遥遥~ 距离提交还剩 24 小时啦，我这边内容已经就位。你那部分进展怎么样？要是有难搞的模块咱今晚碰一下，赶不完的我帮你分担一部分呀~\"\n\n提供协助方案比光催人有诚意多啦！",
      "作为运动搭子，想商量改变打球配合战术，怎么沟通更自然？": "休息喝水的时候随口聊两句：\"刚才对面后场杀球太猛啦！下一局咱俩换个套路试试呗：你网前截击手感快，多在前面蹲抓扑球，我负责满场飞奔跑后场补位，看看能不能直接卡死他们~\"\n\n大大方方聊战术配合，大家都觉得很专业很有默契呢~",
      "想约搭子周末一起去户外徒步，怎么给出轻松无负担的选择？": "发个超松弛的邀约：\"周六打算去走个西山休闲线，大概 6 公里，慢悠悠吸氧不卷步数~ 有空的话一起拼车遛弯呀？要是想宅家补觉也完全 OK，不用有压力哈~\"\n\n给足对方不来的台阶，搭子相处最惬意啦~",
      "搭子在群里发了不太合适的话题，怎么不失尴尬地把话题拉回来？": "哈哈带过就行，千万别严肃说教：\"哈哈行了行了收一收~ 咱们先看回正事哈，刚才聊到 PPT 报告第三部分，大家觉得深色系还是浅色系更高级呀？\"\n\n视线自然平移，尴尬瞬间消失~"
    },
    "defaultReply": "搭子关系贵在舒服和就事论事呀~ 保持明确边界与高效沟通，相处起来最没有包袱啦！"
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
    suggested_opening: '夏夏，今天辛苦啦。先瘫会儿歇着，不想说话就先不聊，等会儿饿了我给你热点吃的~',
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
    suggested_opening: '周总，这趟为 GDP 贡献辛苦了！爽约的账先记上，下周补我一顿饭外加奶茶，地方你选就翻篇~',
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

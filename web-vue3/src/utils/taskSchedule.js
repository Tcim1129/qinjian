export function scheduleDate(scope = 'today', now = new Date()) {
  const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() + (scope === 'tomorrow' ? 1 : 0))
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const tomorrowTasks = [
  { title: '约一个方便聊天的时间', description: '先问问对方明天什么时候有空，不急着聊具体的事。', category: 'communication', target_scope: 'self' },
  { title: '留十分钟一起散步', description: '选一个两个人都不赶时间的空档，聊什么到时候再说。', category: 'activity', target_scope: 'both' },
  { title: '想好一件想分享的小事', description: '可以是一件开心的事，也可以是一句想说却还没说的话。', category: 'reflection', target_scope: 'self' },
]

export function buildDemoSchedule(base = {}, scope = 'today', now = new Date()) {
  const date = scheduleDate(scope, now)
  const tomorrow = scope === 'tomorrow'
  const items = tomorrow
    ? tomorrowTasks.map((task, index) => ({ ...task, id: `demo-plan-${date}-${index}`, source: 'system', status: 'pending', feedback: null, needs_feedback: false }))
    : JSON.parse(JSON.stringify(base.tasks || []))
  const tasks = items.map((task, index) => ({
    ...task, due_date: date,
    importance_level: task.importance_level || (index === 0 ? 'high' : 'medium'),
    refreshable: task.source === 'system' && task.status !== 'completed',
    editable: task.source === 'manual' && task.status !== 'completed',
    importance_adjustable: task.status !== 'completed',
  }))
  return { ...base, tasks, for_date: date, date_scope: tomorrow ? 'tomorrow' : 'today',
    daily_note: tomorrow ? '先留出时间，明天再慢慢做。' : base.daily_note,
    planning_note: tomorrow ? '明日安排' : base.planning_note,
    encouragement_copy: tomorrow ? null : base.encouragement_copy,
    manual_task_count: tasks.filter(task => task.source === 'manual').length,
    manual_task_limit: 10, manual_task_limit_reached: false,
  }
}

export function buildScheduleContext(tasks = [], { scope = 'today', date = scheduleDate(scope), pairId = null, isDemoMode = false, single = false } = {}) {
  const tomorrow = scope === 'tomorrow'
  return {
    pairId, intent: 'plan',
    title: single ? '把这件事拆成小步' : tomorrow ? '一起想想明天怎么安排' : '看看今天先做哪件事',
    sourceLabel: `${date} · ${tomorrow ? '明日安排' : '今日安排'}${isDemoMode ? ' · 样例' : ''}`,
    summary: tasks.length ? tasks.slice(0, 10).map(task => `${task.title || task.label}（${task.status === 'completed' ? '已完成' : '待完成'}）：${task.description || task.note || ''}${task.feedback ? '\n后来：' + describeTaskFeedback(task.feedback) : ''}`).join('\n') : '这一天暂无安排。',
    question: single ? '这件事怎么开始比较容易？帮我想一个小步骤。'
      : tomorrow ? '明天怎么安排比较合适？今晚有什么可以先准备的？'
        : '今天先做哪件事比较合适？我想从简单一点的开始。',
  }
}

export const feedbackOutcomes = [
  { value: 'helped', label: '有帮助' }, { value: 'not_yet', label: '还没做' }, { value: 'difficult', label: '不太顺' },
  { value: 'uncertain', label: '还说不准' },
]

export function buildTaskResultFeedback(task = {}, draft = {}) {
  const previous = task.status === draft.status && task.feedback?.outcome === draft.outcome ? task.feedback || {} : {}
  return feedbackPayload({
    ...previous,
    outcome: draft.status === 'completed'
      ? (['helped', 'difficult', 'uncertain'].includes(draft.outcome) ? draft.outcome : null)
      : 'not_yet',
    note: draft.note,
  })
}

export function buildTaskResultContext(task, { date = task.due_date, pairId = null } = {}) {
  return {
    pairId, intent: 'reflect', title: '聊聊这次的结果', sourceLabel: `${date} · 日常安排`,
    summary: `安排：${task.title}\n状态：${task.status === 'completed' ? '已完成' : '未完成'}\n我的反馈：${task.feedback ? describeTaskFeedback(task.feedback) : '暂未评价'}`,
    question: '结合这次的实际结果，帮我想想接下来怎么做。做了不一定有帮助，没做也不等于失败；不要替我猜测没有提到的原因，必要时再问我一句。也可以先不安排新的事。',
    autoStart: true,
  }
}

export function feedbackPayload(draft = {}) {
  const outcome = feedbackOutcomes.some(item => item.value === draft.outcome) ? draft.outcome : null
  const rating = (value, min, max) => Number.isInteger(value) && value >= min && value <= max ? value : null
  const result = { outcome, note: String(draft.note || '').trim().slice(0, 200),
    usefulness_score: rating(draft.usefulness_score, 1, 5), friction_score: rating(draft.friction_score, 1, 5),
    relationship_shift_score: rating(draft.relationship_shift_score, -2, 2) }
  return outcome || result.note || ['usefulness_score', 'friction_score', 'relationship_shift_score'].some(key => result[key] !== null) ? result : null
}

export function describeTaskFeedback(feedback = {}) {
  return [feedbackOutcomes.find(item => item.value === feedback.outcome)?.label,
    String(feedback.note || '').trim().slice(0, 200),
    feedback.usefulness_score != null ? `有用度 ${feedback.usefulness_score}/5` : '',
    feedback.friction_score != null ? `费劲程度 ${feedback.friction_score}/5` : '',
  ].filter(Boolean).join('；') || '已留下反馈'
}

export function buildTaskFollowupContext(task, { pairId = null, isDemoMode = false, now = new Date() } = {}) {
  const date = scheduleDate('tomorrow', now)
  return {
    pairId, intent: 'plan', title: '接下来怎么做', sourceLabel: `${date} · 明日安排${isDemoMode ? ' · 样例' : ''}`,
    summary: `之前的安排：${task.title || ''}\n原计划日期：${task.due_date || '未注明'}\n状态：${task.status === 'completed' ? '已完成' : '未完成'}\n内容：${task.description || ''}\n我的反馈：${describeTaskFeedback(task.feedback)}`,
    question: '结合这次的结果，明天怎么安排更合适？先给我一个轻一点的办法。',
  }
}

export function createLatestRequest() {
  let version = 0
  return { begin() { const current = ++version; return () => current === version }, invalidate() { version++ } }
}

export function createDemoScheduleCache() {
  const entries = new Map()
  let owner = null
  const clone = value => JSON.parse(JSON.stringify(value))
  function key(scope) {
    if (owner !== scope.owner) { entries.clear(); owner = scope.owner }
    return JSON.stringify([scope.pairId || null, scope.date])
  }
  return {
    read(scope) { const value = entries.get(key(scope)); return value ? clone(value) : null },
    save(scope, payload) { entries.set(key(scope), clone(payload)) },
  }
}

// Only sample data is kept, in memory for this tab. Real schedules always use the API.
export const demoScheduleCache = createDemoScheduleCache()

import { accountStorageKey, getStorageOwner } from './accountStorage.js'

const SOLO_TASKS_KEY = 'qj_solo_tasks_v1'
const SOLO_MILESTONES_KEY = 'qj_solo_milestones_v1'
const SOLO_CONNECTION_KEY = 'qj_solo_connection_v1'

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function readList(key) {
  if (!canUseStorage()) return []
  try {
    const ownerUserId = getStorageOwner()
    const scopedKey = accountStorageKey(key, ownerUserId)
    if (!scopedKey) return []
    const raw = window.localStorage.getItem(scopedKey)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return parsed?.ownerUserId === ownerUserId && Array.isArray(parsed.items) ? parsed.items : []
  } catch {
    return []
  }
}

function writeList(key, value) {
  if (!canUseStorage()) return
  const ownerUserId = getStorageOwner()
  const scopedKey = accountStorageKey(key, ownerUserId)
  if (!scopedKey) throw new Error('请先登录，再保存记录')
  window.localStorage.setItem(scopedKey, JSON.stringify({ ownerUserId, items: value }))
}

export function todayIsoLocal() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

function sortByCreatedAtDesc(items) {
  return [...items].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
}

function buildSoloTaskNote(streak = 0) {
  if (streak >= 7) return '你已经有一段连续节奏了，今天先做一轻一重一收尾。'
  if (streak >= 3) return '这几天节奏开始稳定了，今天先把最容易完成的三步走完。'
  return '先不求做很多，把今天最想推进的三步留出来就够了。'
}

export function buildSoloSystemTasks({ isoDate = todayIsoLocal(), streak = 0 } = {}) {
  const seedTasks = [
    {
      slot: 'checkin',
      title: '先写下今天最想被理解的一句',
      description: '不用把前因后果一次写完，先把最卡住的那一句留住。',
      category: 'reflection',
    },
    {
      slot: 'coach',
      title: streak >= 3 ? '发前看一句话' : '先整理今晚最想怎么开口',
      description: streak >= 3
        ? '看看对方可能怎么听。'
        : '先把想说的话理顺，别在情绪顶点直接发出去。',
      category: 'communication',
    },
    {
      slot: 'close',
      title: '给今天留一个收尾动作',
      description: '比如散步十分钟、写两句复盘，或者约好下一次联系时间。',
      category: 'connection',
    },
  ]

  return seedTasks.map((task, index) => ({
    id: `solo-task-${isoDate}-${task.slot}-${index + 1}`,
    title: task.title,
    description: task.description,
    category: task.category,
    source: 'system',
    target_scope: 'self',
    parent_task_id: null,
    status: 'pending',
    due_date: isoDate,
    created_at: `${isoDate}T08:0${index}:00.000Z`,
    needs_feedback: false,
  }))
}

function buildTaskTree(tasks) {
  const childrenByParent = new Map()
  tasks.forEach((task) => {
    if (!task.parent_task_id) return
    const current = childrenByParent.get(task.parent_task_id) || []
    current.push(task)
    childrenByParent.set(task.parent_task_id, current)
  })

  return sortByCreatedAtDesc(tasks)
    .filter((task) => !task.parent_task_id)
    .map((task) => ({
      ...task,
      children: sortByCreatedAtDesc(childrenByParent.get(task.id) || []),
    }))
}

export function buildSoloTaskPayload({ tasks = [], streak = 0, isoDate = todayIsoLocal() } = {}) {
  const todayTasks = buildTaskTree(
    tasks.filter((task) => String(task.due_date || isoDate) === isoDate)
  ).flatMap((task) => [task, ...(task.children || [])])

  return {
    date: isoDate,
    tasks: todayTasks,
    daily_note: buildSoloTaskNote(streak),
    daily_pack_label: '单人整理',
    combination_insight: '今天先把自己理顺，再决定怎么推进这段关系。',
  }
}

function ensureSoloTasks(tasks, { streak = 0, isoDate = todayIsoLocal() } = {}) {
  const current = Array.isArray(tasks) ? clone(tasks) : []
  const hasTodaySystemTask = current.some(
    (task) => String(task.due_date || '') === isoDate && task.source !== 'manual'
  )
  if (hasTodaySystemTask) return current
  return [...current, ...buildSoloSystemTasks({ isoDate, streak })]
}

export function loadSoloTaskPack({ streak = 0, isoDate = todayIsoLocal() } = {}) {
  const updated = ensureSoloTasks(readList(SOLO_TASKS_KEY), { streak, isoDate })
  writeList(SOLO_TASKS_KEY, updated)
  return buildSoloTaskPayload({ tasks: updated, streak, isoDate })
}

export function createSoloTaskEntry(payload, { streak = 0, isoDate = todayIsoLocal() } = {}) {
  const current = ensureSoloTasks(readList(SOLO_TASKS_KEY), { streak, isoDate })
  const nextTasks = [
    {
      id: `solo-manual-${Date.now()}`,
      title: String(payload.title || '').trim(),
      description: String(payload.description || '').trim(),
      category: String(payload.category || 'activity').trim() || 'activity',
      source: 'manual',
      is_manual: true,
      target_scope: 'self',
      parent_task_id: String(payload.parent_task_id || '').trim() || null,
      status: 'pending',
      due_date: isoDate,
      created_at: new Date().toISOString(),
      needs_feedback: false,
    },
    ...current,
  ]
  writeList(SOLO_TASKS_KEY, nextTasks)
  return buildSoloTaskPayload({ tasks: nextTasks, streak, isoDate })
}

export function completeSoloTaskEntry(taskId, { streak = 0, isoDate = todayIsoLocal() } = {}) {
  const current = ensureSoloTasks(readList(SOLO_TASKS_KEY), { streak, isoDate })
  const nextTasks = current.map((task) =>
    task.id === taskId
      ? {
          ...task,
          status: 'completed',
          needs_feedback: true,
          completed_at: new Date().toISOString(),
        }
      : task
  )
  writeList(SOLO_TASKS_KEY, nextTasks)
  return buildSoloTaskPayload({ tasks: nextTasks, streak, isoDate })
}

export function saveSoloTaskFeedbackEntry(taskId, feedback, { streak = 0, isoDate = todayIsoLocal() } = {}) {
  const current = ensureSoloTasks(readList(SOLO_TASKS_KEY), { streak, isoDate })
  const normalizedFeedback = {
    outcome: ['helped', 'not_yet', 'difficult', 'uncertain'].includes(feedback.outcome) ? feedback.outcome : null,
    usefulness_score: feedback.usefulness_score,
    friction_score: feedback.friction_score,
    relationship_shift_score: feedback.relationship_shift_score,
    note: String(feedback.note || '').trim(),
  }
  const nextTasks = current.map((task) =>
    task.id === taskId
      ? {
          ...task,
          ...(feedback.outcome === 'not_yet' ? { status: 'pending', completed_at: null } : {}),
          feedback: normalizedFeedback,
          needs_feedback: false,
        }
      : task
  )
  writeList(SOLO_TASKS_KEY, nextTasks)
  return buildSoloTaskPayload({ tasks: nextTasks, streak, isoDate })
}

export function saveSoloTaskResultEntry(taskId, result, { streak = 0, isoDate = todayIsoLocal() } = {}) {
  const current = readList(SOLO_TASKS_KEY)
  const task = current.find(item => item.id === taskId)
  if (!task) throw new Error('这条安排已不存在，请重新打开。')
  if (task.due_date > todayIsoLocal()) throw new Error('还没到计划日期，先不用填写结果')
  if (!['pending', 'completed'].includes(result.status) || task.status === 'skipped') throw new Error('这条安排暂时不能修改结果')
  const completed = result.status === 'completed'
  const next = current.map(item => item.id === taskId ? {
    ...item, status: result.status, completed_at: completed ? item.completed_at || new Date().toISOString() : null,
    feedback: result.feedback, needs_feedback: completed && !result.feedback,
  } : item)
  writeList(SOLO_TASKS_KEY, next)
  return buildSoloTaskPayload({ tasks: next, streak, isoDate })
}

export function loadSoloMilestoneEntries() {
  return sortByCreatedAtDesc(readList(SOLO_MILESTONES_KEY)).map((item) => clone(item))
}

export function createSoloMilestoneEntry(payload) {
  const nextEntries = [
    {
      id: `solo-milestone-${Date.now()}`,
      type: String(payload.type || 'custom').trim() || 'custom',
      title: String(payload.title || '').trim(),
      date: String(payload.date || '').trim(),
      created_at: new Date().toISOString(),
      source: 'solo',
    },
    ...readList(SOLO_MILESTONES_KEY),
  ]
  writeList(SOLO_MILESTONES_KEY, nextEntries)
  return loadSoloMilestoneEntries()
}

export function buildSoloConnectionHealth(activities = []) {
  const recentActivities = Array.isArray(activities)
    ? activities.filter((activity) => String(activity.created_at || '').slice(0, 10) >= todayIsoLocal().slice(0, 8) + '01')
    : []
  const completedCount = recentActivities.filter((activity) => activity.status === 'completed').length
  const pendingCount = recentActivities.filter((activity) => activity.status !== 'completed').length
  const activityCount = recentActivities.length
  const healthIndex = Math.max(
    28,
    Math.min(100, 32 + completedCount * 18 + pendingCount * 9 + Math.min(activityCount, 4) * 5)
  )

  return {
    health_index: healthIndex,
    plan_count: activityCount,
    completed_count: completedCount,
    pending_count: pendingCount,
    summary: activityCount
      ? '你已经在给下一次联系留位置了，继续把计划变成一个具体动作。'
      : '还没有具体安排时，先留一个轻量计划，关系会比空想更稳。',
  }
}

export function loadSoloConnectionWorkspace() {
  const activities = sortByCreatedAtDesc(readList(SOLO_CONNECTION_KEY)).map((item) => clone(item))
  return {
    health: buildSoloConnectionHealth(activities),
    activities,
  }
}

export function createSoloConnectionActivityEntry(activityType, title = '') {
  const nextEntries = [
    {
      id: `solo-connection-${Date.now()}`,
      activity_type: String(activityType || 'chat').trim() || 'chat',
      type: String(activityType || 'chat').trim() || 'chat',
      title: String(title || '').trim(),
      status: 'pending',
      created_at: new Date().toISOString(),
      source: 'solo',
    },
    ...readList(SOLO_CONNECTION_KEY),
  ]
  writeList(SOLO_CONNECTION_KEY, nextEntries)
  return loadSoloConnectionWorkspace()
}

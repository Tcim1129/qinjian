import { defineStore } from 'pinia'
import { api } from '@/api'
import { ref } from 'vue'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { getAuthToken, isDemoToken } from '@/utils/auth'
import { collectEnergyNodeLocally, normalizeEnergyNodes } from '@/utils/relationshipTreeEnergy'
import { createLatestRequest } from '@/utils/taskSchedule'

const DAY_MS = 24 * 60 * 60 * 1000
const DEFAULT_WATER_BONUS = 12
const DEFAULT_DECAY_PER_DAY = 0
const DEFAULT_DECAY_GRACE_DAYS = 1

function isDemoMode() {
  return isDemoToken()
}

function clampNumber(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min))
}

function parseDateOnly(value) {
  if (!value) return null
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function todayDateOnly() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

function todayIso() {
  return isoDaysAgo(0)
}

function isoDaysAgo(days) {
  const today = todayDateOnly()
  today.setDate(today.getDate() - Math.max(0, Number(days || 0)))
  const pad = (value) => String(value).padStart(2, '0')
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`
}

function daysSince(dateString) {
  const date = parseDateOnly(dateString)
  if (!date) return 0
  return Math.max(0, Math.floor((todayDateOnly() - date) / DAY_MS))
}

function calcProgress(points, nextLevelAt, fallback = 0) {
  const limit = Number(nextLevelAt || 0)
  if (limit > 0) return Math.round(clampNumber((Number(points || 0) / limit) * 100))
  return Math.round(clampNumber(Number(fallback || 0)))
}

function withTreeDerivedFields(input = {}) {
  const base = input || {}
  const growthPoints = Math.max(0, Number(base.growth_points || 0))
  const energyNodes = normalizeEnergyNodes(base.energy_nodes || base.energy_bubbles || [])
  const waterBonus = Math.max(1, Number(base.water_bonus || base.points_added || DEFAULT_WATER_BONUS))
  const decayPerDay = Math.max(0, Number(base.decay_per_day ?? DEFAULT_DECAY_PER_DAY))
  const decayGraceDays = Math.max(0, Number(base.decay_grace_days ?? DEFAULT_DECAY_GRACE_DAYS))
  const daysWithoutWater = daysSince(base.last_watered)
  // The server owns the balance. Do not fabricate score loss from a local clock.
  const decayPoints = Math.min(growthPoints, Math.max(0, Number(base.decay_points || 0)))
  const effectiveGrowthPoints = Math.max(0, growthPoints - decayPoints)
  const progressPercent = calcProgress(growthPoints, base.next_level_at, base.progress_percent)
  const displayProgressPercent = calcProgress(effectiveGrowthPoints, base.next_level_at, base.progress_percent)
  const canWater = typeof base.can_water === 'boolean'
    ? base.can_water
    : energyNodes.some((node) => node.available)

  return {
    ...base,
    growth_points: growthPoints,
    energy_nodes: energyNodes,
    water_bonus: waterBonus,
    decay_per_day: decayPerDay,
    decay_grace_days: decayGraceDays,
    days_without_water: daysWithoutWater,
    decay_points: decayPoints,
    effective_growth_points: effectiveGrowthPoints,
    progress_percent: progressPercent,
    display_progress_percent: displayProgressPercent,
    decay_progress_percent: Math.max(0, progressPercent - displayProgressPercent),
    can_water: canWater,
  }
}

export const useHomeStore = defineStore('home', () => {
  const snapshot = ref(null)
  const tree = ref({})
  const crisis = ref({})
  const tasks = ref([])
  const dailyNote = ref('')
  const milestones = ref([])
  const loads = createLatestRequest()
  const demoTrees = new Map()
  let treeScope = null

  function reset() {
    loads.invalidate()
    demoTrees.clear()
    treeScope = null
    snapshot.value = null
    tree.value = {}
    crisis.value = {}
    tasks.value = []
    dailyNote.value = ''
    milestones.value = []
  }

  async function loadAll(pairId = null) {
    const requestCurrent = loads.begin()
    const token = getAuthToken()
    const current = () => requestCurrent() && token === getAuthToken()
    treeScope = pairId
    tree.value = {}
    if (isDemoMode()) {
      snapshot.value = {
        todayStatus: cloneDemo(demoFixture.todayStatus),
        streak: cloneDemo(demoFixture.streak),
      }
      tree.value = demoTrees.get(`${pairId}:${todayIso()}`) || withTreeDerivedFields({
        ...cloneDemo(demoFixture.tree),
        last_watered: isoDaysAgo(13),
      })
      crisis.value = cloneDemo(demoFixture.crisis)
      tasks.value = cloneDemo((demoFixture.tasks.tasks || []).filter((task) => task.source !== 'manual').slice(0, 3))
      dailyNote.value = demoFixture.tasks.daily_note || ''
      milestones.value = []
      return
    }

    if (!pairId) {
      const results = await Promise.allSettled([
        api.getTodayStatus(null),
        api.getCheckinStreak(null),
      ])
      if (!current()) return
      const unwrap = (r, fallback = {}) => r.status === 'fulfilled' ? r.value : fallback

      snapshot.value = {
        todayStatus: unwrap(results[0]),
        streak: unwrap(results[1]),
      }
      tree.value = {}
      crisis.value = {}
      tasks.value = []
      dailyNote.value = ''
      milestones.value = []
      return
    }

    const results = await Promise.allSettled([
      api.getTodayStatus(pairId),
      api.getCheckinStreak(pairId),
      api.getTreeStatus(pairId),
      api.getCrisisStatus(pairId),
      api.getDailyTasks(pairId),
      api.getMilestones(pairId),
    ])
    if (!current()) return
    const unwrap = (r, fallback = {}) => r.status === 'fulfilled' ? r.value : fallback

    snapshot.value = {
      todayStatus: unwrap(results[0]),
      streak: unwrap(results[1]),
    }
    tree.value = withTreeDerivedFields(unwrap(results[2]))
    crisis.value = unwrap(results[3])
    const dailyPayload = unwrap(results[4], { tasks: [] })
    tasks.value = (dailyPayload.tasks || []).filter((task) => task.source !== 'manual').slice(0, 3)
    dailyNote.value = dailyPayload.daily_note || ''
    milestones.value = unwrap(results[5], [])
  }

  async function waterTree(pairId) {
    if (isDemoMode()) {
      const current = Object.keys(tree.value || {}).length ? tree.value : withTreeDerivedFields(cloneDemo(demoFixture.tree))
      const pointsAdded = Number(current.water_bonus || DEFAULT_WATER_BONUS)
      const nextLevelAt = Number(current.next_level_at || 0)
      const baseGrowth = Number(current.effective_growth_points ?? current.growth_points ?? 0)
      const nextGrowth = nextLevelAt > 0 ? Math.min(nextLevelAt, baseGrowth + pointsAdded) : baseGrowth + pointsAdded
      tree.value = withTreeDerivedFields({
        ...current,
        growth_points: nextGrowth,
        last_watered: todayIso(),
        can_water: false,
        points_added: pointsAdded,
      })
      return tree.value
    }

    const result = await api.waterTree(pairId)
    tree.value = withTreeDerivedFields({
      ...tree.value,
      ...result,
      last_watered: todayIso(),
      can_water: false,
    })
    return tree.value
  }

  async function collectTreeEnergy(pairId, nodeKey) {
    const expectedTree = tree.value
    const token = getAuthToken()
    if (treeScope !== pairId) throw new Error('关系已切换，请重新收取')
    if (isDemoMode()) {
      const current = Object.keys(tree.value || {}).length ? tree.value : withTreeDerivedFields(cloneDemo(demoFixture.tree))
      tree.value = withTreeDerivedFields({
        ...collectEnergyNodeLocally(current, nodeKey),
        last_watered: todayIso(),
      })
      demoTrees.set(`${pairId}:${todayIso()}`, tree.value)
      return tree.value
    }

    const result = await api.collectTreeEnergy(pairId, nodeKey)
    if (treeScope !== pairId || tree.value !== expectedTree || token !== getAuthToken()) throw new Error('关系已刷新，请重新查看成长值')
    tree.value = withTreeDerivedFields({
      ...tree.value,
      ...result,
    })
    return tree.value
  }

  async function completeTask(taskId) {
    return api.completeTask(taskId)
  }

  return { snapshot, tree, crisis, tasks, dailyNote, milestones, loadAll, waterTree, collectTreeEnergy, completeTask, reset }
})

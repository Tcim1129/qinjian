export const RELATIONSHIP_TREE_ENERGY_RULES = [
  {
    key: 'my_record',
    label: '记录',
    points: 10,
    lockedHint: '去记录后出现',
  },
  {
    key: 'partner_record',
    label: '同步',
    points: 8,
    lockedHint: '等对方同步',
  },
  {
    key: 'small_repair',
    label: '小行动',
    points: 12,
    lockedHint: '完成小行动后出现',
  },
]

function parsePoints(value, fallback) {
  const explicit = Number(value)
  if (Number.isFinite(explicit) && explicit > 0) return explicit
  const match = String(value || '').match(/-?\d+/)
  const parsed = match ? Number(match[0]) : Number(fallback)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : Number(fallback)
}

function inferNodeKey(item = {}) {
  const explicit = String(item.key || '').trim()
  if (explicit) return explicit
  const label = String(item.label || '').trim()
  if (label.includes('记录')) return 'my_record'
  if (label.includes('同步') || label.includes('回应') || label.includes('共情')) return 'partner_record'
  if (label.includes('行动') || label.includes('缓和')) return 'small_repair'
  return ''
}

function normalizeNodeState(item, hasLegacyItem) {
  const state = String(item?.state || '').trim()
  const collected = Boolean(item?.collected) || state === 'collected'
  if (collected) {
    return { state: 'collected', collected: true, available: false, hint: '已抓取' }
  }

  const available = typeof item?.available === 'boolean'
    ? item.available
    : state
      ? state === 'available'
      : hasLegacyItem

  if (available) {
    return { state: 'available', collected: false, available: true, hint: item?.hint || '点击抓取成长值' }
  }

  return { state: 'locked', collected: false, available: false, hint: item?.hint || '' }
}

export function normalizeEnergyNodes(input = []) {
  const byKey = new Map()
  ;(Array.isArray(input) ? input : []).forEach((item) => {
    const key = inferNodeKey(item)
    if (key && !byKey.has(key)) byKey.set(key, item)
  })

  return RELATIONSHIP_TREE_ENERGY_RULES.map((rule) => {
    const item = byKey.get(rule.key)
    const state = normalizeNodeState(item, Boolean(item))
    const points = parsePoints(item?.points ?? item?.value, rule.points)
    return {
      key: rule.key,
      label: rule.label,
      points,
      value: `+${points}`,
      state: state.state,
      collected: state.collected,
      available: state.available,
      hint: state.hint || rule.lockedHint,
    }
  })
}

export function collectEnergyNodeLocally(tree = {}, nodeKey) {
  const nodes = normalizeEnergyNodes(tree.energy_nodes || tree.energy_bubbles || [])
  const target = nodes.find((node) => node.key === nodeKey)
  if (!target) throw new Error('这个能量节点不存在')
  if (target.collected) throw new Error('这个节点今天已经抓取过了')
  if (!target.available) throw new Error(target.hint || '这个节点还不能抓取')

  const updatedNodes = nodes.map((node) => (
    node.key === nodeKey
      ? { ...node, state: 'collected', collected: true, available: false, hint: '已抓取' }
      : node
  ))
  const growthPoints = Math.max(0, Number(tree.effective_growth_points ?? tree.growth_points ?? 0))
  return {
    ...tree,
    growth_points: growthPoints + target.points,
    energy_nodes: updatedNodes,
    points_added: target.points,
    can_water: updatedNodes.some((node) => node.available),
  }
}

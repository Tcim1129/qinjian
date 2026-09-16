import { relationshipTypeLabel } from './displayText.js'
import { buildPairStatusSummary } from './pairStatusSummary.js'
import { getPartnerDisplayName } from './relationshipSpaces.js'

const DISTANCE_BY_SCORE = [
  { min: 80, radius: 132 },
  { min: 65, radius: 176 },
  { min: 0, radius: 224 },
]

const MAX_STAR_NODES = 12
const MAX_VISIBLE_RELATION_NODES = 11
const INNER_RING_LIMIT = 5
const INNER_RING_RADIUS = 148
const OUTER_RING_RADIUS = 228
const FOCUS_ARC_START = (-5 * Math.PI) / 6
const FOCUS_ARC_END = -Math.PI / 6

const TREND_LABELS = {
  up: '在变好',
  down: '有点紧',
  flat: '比较稳定',
}

const STAGE_LABELS = {
  up: '最近在变好',
  down: '最近有点紧',
  flat: '最近比较稳',
}

function normalizeScore(value) {
  if (value === null || value === undefined || value === '') return null
  const score = Number(value)
  if (Number.isFinite(score)) return Math.max(0, Math.min(100, Math.round(score)))
  return null
}

function normalizeTrend(value) {
  const trend = String(value || 'flat').trim().toLowerCase()
  return trend === 'up' || trend === 'down' ? trend : 'flat'
}

function visualStateFrom(score, trend, isSelected) {
  const hasScore = Number.isFinite(score)
  return {
    glow: isSelected ? 'focused' : !hasScore ? 'soft' : score >= 80 ? 'strong' : score >= 65 ? 'steady' : 'soft',
    line: isSelected ? 'focused' : trend === 'up' ? 'warm' : trend === 'down' ? 'dim' : 'steady',
    emphasis: isSelected || (hasScore && score >= 80) ? 'primary' : 'secondary',
  }
}

function scoreDistanceNudge(score, trend) {
  if (!Number.isFinite(score)) return 0
  const bucket = DISTANCE_BY_SCORE.find((item) => score >= item.min) || DISTANCE_BY_SCORE[DISTANCE_BY_SCORE.length - 1]
  const bucketOffset = bucket.radius <= 140 ? -8 : bucket.radius >= 220 ? 8 : 0
  const trendOffset = trend === 'up' ? -8 : trend === 'down' ? 8 : 0
  return bucketOffset + trendOffset
}

function sortNodesForDisplay(a, b) {
  const aHasScore = Number.isFinite(a.score)
  const bHasScore = Number.isFinite(b.score)
  if (aHasScore && bHasScore && b.score !== a.score) return b.score - a.score
  return String(a.label || '').localeCompare(String(b.label || ''), 'zh-Hans-CN')
}

function overflowVisualState() {
  return {
    glow: 'soft',
    line: 'steady',
    emphasis: 'secondary',
  }
}

function buildSidebar(pair, metric, label) {
  return buildPairStatusSummary({ pair, metric, label })
}

function buildPairNode(pair, metric, currentPairId) {
  const label = getPartnerDisplayName(pair)
  const summary = buildSidebar(pair, metric, label)
  const score = normalizeScore(metric?.score)
  const trend = normalizeTrend(metric?.trend)
  const isSelected = pair.id === currentPairId

  return {
    id: `relationship-node-${pair.id}`,
    kind: 'pair',
    pairId: pair.id,
    label,
    shortLabel: String(label || '对').slice(0, 1),
    typeLabel: relationshipTypeLabel(pair?.type),
    score,
    trend,
    distance: 0,
    angle: 0,
    isSelected,
    visualState: visualStateFrom(score, trend, isSelected),
    sidebar: summary,
  }
}

function buildOverflowNode(hiddenNodes) {
  const hiddenCount = hiddenNodes.length

  return {
    id: 'relationship-node-overflow',
    kind: 'overflow',
    pairId: '__overflow__',
    label: `+${hiddenCount}`,
    shortLabel: `+${hiddenCount}`,
    typeLabel: '更多关系',
    score: hiddenCount,
    trend: 'flat',
    distance: 0,
    angle: 0,
    isSelected: false,
    visualState: overflowVisualState(),
    sidebar: {
      kind: 'overflow',
      pairId: '',
      title: '更多关系',
      typeLabel: '列表自动收纳',
      statusLabel: `已收起 ${hiddenCount} 段`,
      score: hiddenCount,
      scoreLabel: `+${hiddenCount}`,
      scoreHeading: '已收起',
      trend: 'flat',
      trendLabel: '关系太多时会自动收纳最外层',
      summary: `还有 ${hiddenCount} 段已收起。`,
      recentSummary: `还有 ${hiddenCount} 段已收起。`,
      nextAction: '从关系列表继续查看。',
      hiddenPairs: hiddenNodes.map((node) => ({
        pairId: node.pairId,
        title: node.label,
        typeLabel: node.typeLabel,
        score: node.score,
        trendLabel: node.sidebar?.trendLabel || TREND_LABELS.flat,
      })),
    },
  }
}

function buildDisplayNodes(nodes, currentPairId) {
  const sortedNodes = [...nodes].sort(sortNodesForDisplay)
  if (sortedNodes.length <= MAX_STAR_NODES) return sortedNodes

  const selectedNode = sortedNodes.find((node) => node.pairId === currentPairId) || null
  const visibleNodes = sortedNodes.slice(0, MAX_VISIBLE_RELATION_NODES)

  if (selectedNode && !visibleNodes.some((node) => node.pairId === selectedNode.pairId)) {
    visibleNodes[MAX_VISIBLE_RELATION_NODES - 1] = selectedNode
  }

  const visibleIds = new Set(visibleNodes.map((node) => node.pairId))
  const hiddenNodes = sortedNodes.filter((node) => !visibleIds.has(node.pairId))
  const overflowNode = buildOverflowNode(hiddenNodes)

  return [...visibleNodes.sort(sortNodesForDisplay), overflowNode]
}

function layoutDisplayNodes(nodes) {
  if (!nodes.length) return []

  const innerCount = nodes.length <= 6 ? nodes.length : Math.min(INNER_RING_LIMIT, nodes.length)
  const ringCounts = nodes.length <= 6 ? [innerCount] : [innerCount, nodes.length - innerCount]
  let startIndex = 0

  return ringCounts.flatMap((ringCount, ringIndex) => {
    const ringNodes = nodes.slice(startIndex, startIndex + ringCount)
    startIndex += ringCount
    const ringBaseRadius = ringIndex === 0 ? INNER_RING_RADIUS : OUTER_RING_RADIUS
    const ringOffset = ringIndex === 0 ? -Math.PI / 2 : -Math.PI / 2 + Math.PI / Math.max(ringCount, 1)
    const step = (Math.PI * 2) / Math.max(ringCount, 1)

    return ringNodes.map((node, slotIndex) => {
      const angle = ringCount === 1 ? -Math.PI / 2 : ringOffset + step * slotIndex
      const distance = node.kind === 'overflow'
        ? ringBaseRadius + 12
        : ringBaseRadius + scoreDistanceNudge(node.score, node.trend)
      const size = node.kind === 'overflow'
        ? 54
        : nodes.length > 10
          ? 58
          : nodes.length > 6
            ? ringIndex === 0 ? 66 : 62
            : 74

      return {
        ...node,
        angle,
        distance,
        ringIndex,
        ringCount,
        size,
        labelOffset: Math.max(20, Math.round(size / 2.6)),
      }
    })
  })
}

function buildFocusModeNodes(nodes, focusPairId) {
  const focusNode = nodes.find((node) => node.pairId === focusPairId && node.kind === 'pair') || null
  if (!focusNode) {
    return {
      focusNode: null,
      nodes,
    }
  }

  const outerSourceNodes = nodes.filter((node) => node.pairId !== focusPairId)
  const outerStep = outerSourceNodes.length > 1
    ? (FOCUS_ARC_END - FOCUS_ARC_START) / (outerSourceNodes.length - 1)
    : 0

  const outerNodes = outerSourceNodes.map((node, index) => ({
      ...node,
      angle: outerSourceNodes.length === 1 ? -Math.PI / 2 : FOCUS_ARC_START + outerStep * index,
      distance: Math.max(
        196 + (index % 2) * 24 + (node.kind === 'overflow' ? 12 : 0),
        node.distance + (node.ringIndex === 0 ? 72 : 50)
      ),
      size: Math.max(node.kind === 'overflow' ? 46 : 40, node.size - (node.kind === 'overflow' ? 8 : 16)),
      labelOffset: Math.max(14, node.labelOffset - 6),
      isPeripheral: true,
      visualState: {
        ...node.visualState,
        glow: node.kind === 'overflow' ? 'soft' : 'steady',
        line: node.visualState?.line === 'warm' ? 'warm' : 'dim',
        emphasis: 'secondary',
      },
    }))

  return {
    focusNode: {
      ...focusNode,
      focusSummary: `${focusNode.typeLabel} · ${focusNode.sidebar?.trendLabel || ''}`.trim(),
      focusDetail: focusNode.sidebar?.recentSummary || '',
    },
    nodes: outerNodes,
  }
}

export function buildRelationshipSpaceModel({ me, currentPairId, focusPairId = '', pairs = [], metricsByPairId = {} } = {}) {
  const center = {
    id: me?.id || 'self',
    label: String(me?.nickname || '').trim() || '我',
  }

  const pairNodes = pairs.map((pair) => buildPairNode(pair, metricsByPairId[pair.id], currentPairId))
  const layoutNodes = layoutDisplayNodes(buildDisplayNodes(pairNodes, currentPairId))
  const { nodes, focusNode } = buildFocusModeNodes(layoutNodes, focusPairId)

  const selectedNode = focusNode || nodes.find((node) => node.pairId === currentPairId) || nodes[0] || null

  return {
    center,
    focusPairId: focusNode?.pairId || '',
    focusNode,
    nodes,
    selectedPairId: selectedNode?.pairId || '',
    selectedSidebar: selectedNode?.sidebar || null,
  }
}

export function buildRelationshipSpaceDetailModel({ me, pair, metricsByPairId = {}, moments = [] } = {}) {
  const label = getPartnerDisplayName(pair)
  const sidebar = buildSidebar(pair, metricsByPairId[pair?.id], label)
  const myName = String(me?.nickname || '').trim() || '我'
  const stageLabel = sidebar.hasScore
    ? (STAGE_LABELS[sidebar.trend] || STAGE_LABELS.flat)
    : pair?.status === 'active'
      ? '关系已建立'
      : '等待对方加入'

  return {
    hero: {
      title: `${myName} · ${label}`,
      subtitle: `${relationshipTypeLabel(pair?.type)} · ${sidebar.statusLabel}`,
      score: sidebar.score,
      trendLabel: sidebar.trendLabel,
      stageLabel,
      summary: sidebar.summary,
    },
    moments: moments.length
      ? moments
      : ['已单独记录。', '从最近一次互动继续看。'],
    primaryAction: {
      label: pair?.status === 'active' ? '先约一个简单聊天或电话' : '先把邀请码发给对方',
      description: sidebar.nextAction,
    },
    scoreCard: {
      score: sidebar.score,
      scoreHeading: sidebar.scoreHeading,
      scoreLabel: sidebar.scoreLabel,
      trendLabel: sidebar.trendLabel,
      summary: sidebar.summary,
    },
  }
}

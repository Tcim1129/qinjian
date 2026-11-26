import { formatBeijingShortDate } from './datetime.js'

const DEMO_HOME_TREND_POINTS = [
  { label: '30天前', x: 28, y: 112, score: 58 },
  { label: '24天前', x: 88.8, y: 98, score: 63 },
  { label: '18天前', x: 149.6, y: 104, score: 61 },
  { label: '12天前', x: 210.4, y: 76, score: 72 },
  { label: '6天前', x: 271.2, y: 68, score: 75 },
  { label: '今天', x: 332, y: 46, score: 82 },
].map((point) => ({
  ...point,
  labelY: Math.max(18, point.y - 10),
  axisX: Number(((point.x / 360) * 100).toFixed(2)),
}))

const RADAR_VERTICES = [
  { id: 'connection', label: '表达', x: 110, y: 24 },
  { id: 'trust', label: '信任', x: 192, y: 84 },
  { id: 'repair', label: '缓和', x: 161, y: 180 },
  { id: 'shared_future', label: '愿景', x: 59, y: 180 },
  { id: 'vitality', label: '活力', x: 28, y: 84 },
]

const DEMO_RADAR_SCORES = {
  connection: 72,
  trust: 64,
  repair: 70,
  shared_future: 58,
  vitality: 76,
}

function clampScore(value) {
  if (value == null || typeof value === 'boolean' || (typeof value === 'string' && !value.trim())) return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  return Math.min(100, Math.max(0, Math.round(num)))
}

function scoreToY(score) {
  // SVG viewBox 360x150，底部基准线在 y=126，顶部安全区在 y=28
  return Number((122 - score * 0.88).toFixed(1))
}

function toChartPoints(rawPoints) {
  const sliced = rawPoints.slice(-6)
  if (!sliced.length) return []
  const span = 304 // x 从 28 到 332
  return sliced.map((item, index) => {
    const x = sliced.length === 1
      ? 180
      : Number((28 + (span * index) / (sliced.length - 1)).toFixed(1))
    const y = scoreToY(item.score)
    return {
      key: `${item.label}-${index}`,
      label: item.label,
      score: item.score,
      x,
      y,
      labelY: Math.max(18, Number((y - 10).toFixed(1))),
      axisX: Number(((x / 360) * 100).toFixed(2)),
    }
  })
}

export function buildHomeTrendView({ isDemoMode = false, reportTrend = null, assessmentTrend = null } = {}) {
  if (isDemoMode) {
    return {
      points: DEMO_HOME_TREND_POINTS.map((point, index) => ({ ...point, key: `demo-${index}` })),
      badge: '样例趋势',
    }
  }

  const reportSeries = (Array.isArray(reportTrend?.trend) ? reportTrend.trend : [])
    .map((item, index) => {
      const score = clampScore(item?.score)
      if (score === null) return null
      return {
        label: formatBeijingShortDate(item?.date) || `第${index + 1}次`,
        score,
      }
    })
    .filter(Boolean)

  const assessmentSeries = (Array.isArray(assessmentTrend?.trend_points) ? assessmentTrend.trend_points : [])
    .map((item, index) => {
      const score = clampScore(item?.total_score)
      if (score === null) return null
      return {
        label: formatBeijingShortDate(item?.submitted_at) || `第${index + 1}次`,
        score,
      }
    })
    .filter(Boolean)

  const useReports = reportSeries.length >= 2 || (reportSeries.length > 0 && assessmentSeries.length === 0)
  const chosen = useReports ? reportSeries : assessmentSeries
  if (!chosen.length) {
    return { points: [], badge: '暂无数据' }
  }

  const points = toChartPoints(chosen)
  const latestScore = points[points.length - 1].score
  const sourceTag = useReports ? '简报趋势' : '体检趋势'
  const badge = points.length >= 2 ? `${sourceTag} · ${latestScore}分` : `${sourceTag} · ${latestScore}分`
  return { points, badge }
}

function projectRadarAxes(scoreMap) {
  const center = { x: 110, y: 110 }
  return RADAR_VERTICES.map((vertex) => {
    const value = clampScore(scoreMap[vertex.id]) ?? 0
    const ratio = value / 100
    const dx = vertex.x - center.x
    const dy = vertex.y - center.y
    const length = Math.hypot(dx, dy) || 1
    const unitX = dx / length
    const unitY = dy / length
    return {
      ...vertex,
      value,
      valueX: Number((center.x + dx * ratio).toFixed(1)),
      valueY: Number((center.y + dy * ratio).toFixed(1)),
      valueLabelX: Number((center.x + dx * ratio + unitX * 12).toFixed(1)),
      valueLabelY: Number((center.y + dy * ratio + unitY * 12 + 4).toFixed(1)),
      valueTextAnchor: vertex.x > 130 ? 'start' : vertex.x < 90 ? 'end' : 'middle',
      labelX: Number((vertex.x + unitX * 18).toFixed(1)),
      labelY: Number((vertex.y + unitY * 18 + 4).toFixed(1)),
      labelAnchor: vertex.x > 130 ? 'start' : vertex.x < 90 ? 'end' : 'middle',
    }
  })
}

export function buildHomeRadarAxes({ isDemoMode = false, assessmentTrend = null } = {}) {
  if (isDemoMode) {
    return projectRadarAxes(DEMO_RADAR_SCORES)
  }

  let rawDimensions = Array.isArray(assessmentTrend?.dimension_scores)
    ? assessmentTrend.dimension_scores
    : []
  if (!rawDimensions.length && Array.isArray(assessmentTrend?.trend_points) && assessmentTrend.trend_points.length) {
    const latestPoint = assessmentTrend.trend_points[assessmentTrend.trend_points.length - 1]
    if (Array.isArray(latestPoint?.dimension_scores)) {
      rawDimensions = latestPoint.dimension_scores
    }
  }

  const scoreMap = {}
  for (const item of rawDimensions) {
    const id = String(item?.id || '').trim()
    const score = clampScore(item?.score)
    if (id && score !== null) {
      scoreMap[id] = score
    }
  }
  if (!RADAR_VERTICES.every(vertex => scoreMap[vertex.id] !== undefined)) return []
  return projectRadarAxes(scoreMap)
}

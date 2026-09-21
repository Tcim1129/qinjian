export const RADAR_CENTER = { x: 220, y: 200 }
export const RADAR_RADIUS = 108
const RADAR_LABEL_RADIUS = 146

export function normalizeChartScore(value) {
  if (value == null || String(value).trim() === '') return null
  const score = Number(value)
  return Number.isFinite(score) && score >= 0 && score <= 100 ? score : null
}

export function buildRadarAxes(dimensions = []) {
  return dimensions.map((item, index) => {
    const angle = (-90 + index * 360 / dimensions.length) * Math.PI / 180
    const dx = Math.cos(angle), dy = Math.sin(angle)
    const score = normalizeChartScore(item.score) ?? 0
    const labelX = RADAR_CENTER.x + dx * RADAR_LABEL_RADIUS
    const labelY = RADAR_CENTER.y + dy * RADAR_LABEL_RADIUS
    const characters = Array.from(String(item.label || ''))
    const labelLines = []
    for (let i = 0; i < characters.length; i += 4) labelLines.push(characters.slice(i, i + 4).join(''))
    return {
      ...item, score, labelLines,
      axisX: RADAR_CENTER.x + dx * RADAR_RADIUS,
      axisY: RADAR_CENTER.y + dy * RADAR_RADIUS,
      valueX: RADAR_CENTER.x + dx * RADAR_RADIUS * score / 100,
      valueY: RADAR_CENTER.y + dy * RADAR_RADIUS * score / 100,
      labelX, labelY,
      valueLabelX: labelX, valueLabelY: labelY + 21,
      labelStartY: labelY - 12 - (labelLines.length - 1) * 20,
      anchor: dx > 0.2 ? 'start' : dx < -0.2 ? 'end' : 'middle',
    }
  })
}

export function radarPolygon(percent, count = 5) {
  if (count < 3) return ''
  return Array.from({ length: count }, (_, index) => {
    const angle = (-90 + index * 360 / count) * Math.PI / 180
    const radius = RADAR_RADIUS * percent / 100
    return `${(RADAR_CENTER.x + Math.cos(angle) * radius).toFixed(1)},${(RADAR_CENTER.y + Math.sin(angle) * radius).toFixed(1)}`
  }).join(' ')
}

export function buildTrendChart(input = []) {
  const data = input.map(item => ({ ...item, score: normalizeChartScore(item.score) })).filter(item => item.score !== null)
  const width = Math.max(440, 96 + (data.length - 1) * 58)
  const left = 52, right = width - 24, top = 48, bottom = 232
  if (!data.length) return { points: [], ticks: [], delta: null, min: 0, max: 100, width, left, right, top, bottom }
  const scores = data.map(item => item.score)
  const low = Math.min(...scores), high = Math.max(...scores)
  // A minimum 20-point window makes small changes legible without magnifying them into spikes.
  const span = Math.min(100, Math.max(20, high - low + 8))
  const tickStep = span <= 25 ? 5 : span <= 50 ? 10 : 25
  const lower = Math.max(0, Math.min(100 - span, (low + high - span) / 2))
  const min = Math.floor(lower / tickStep) * tickStep
  const max = Math.min(100, Math.ceil((lower + span) / tickStep) * tickStep)
  const scoreY = score => bottom - (score - min) / (max - min) * (bottom - top)
  const ticks = []
  for (let score = min; score <= max; score += tickStep) ticks.push({ score, y: scoreY(score) })
  const points = data.map((item, index) => ({
    ...item,
    shortLabel: String(item.label || '').replace(/(\d+)月(\d+)日/, '$1/$2'),
    x: data.length === 1 ? (left + right) / 2 : left + 22 + index * (right - left - 34) / (data.length - 1),
    y: scoreY(item.score),
  }))
  const delta = data.length > 1 ? Number((scores.at(-1) - scores.at(-2)).toFixed(1)) : null
  return { points, ticks, delta, min, max, width, left, right, top, bottom }
}

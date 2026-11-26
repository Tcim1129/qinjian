export function normalizeReportList(value) {
  if (Array.isArray(value)) return value.filter((item) => Boolean(String(item || '').trim()))
  if (typeof value === 'string' && value.trim()) return [value.trim()]
  return []
}

export function firstNonEmptyList(candidates = []) {
  for (const candidate of candidates) {
    const normalized = normalizeReportList(candidate)
    if (normalized.length) return normalized
  }
  return []
}

export function extractReportSummary(report) {
  const candidates = [
    report?.summary,
    report?.content?.insight,
    report?.content?.self_insight,
    report?.content?.executive_summary,
    report?.content?.trend_description,
    report?.content?.suggestion,
    report?.content?.self_care_tip,
  ]
  for (const item of candidates) {
    const text = String(item || '').trim()
    if (text) return text
  }
  return '暂无结论'
}

export function extractReportInsights(report) {
  const structured = firstNonEmptyList([
    report?.content?.highlights,
    report?.content?.weekly_highlights,
    report?.content?.strengths,
    report?.key_insights,
  ])
  if (structured.length) return structured

  const soloFields = normalizeReportList([
    report?.content?.emotional_pattern,
    report?.content?.relationship_note,
    report?.content?.communication_analysis,
  ])
  if (soloFields.length) return soloFields

  return firstNonEmptyList([
    report?.evidence_summary,
  ])
}

export function extractReportRecommendations(report) {
  const primary = firstNonEmptyList([
    report?.content?.action_plan,
    report?.content?.next_month_goals,
    report?.content?.intervention?.action_items,
    report?.recommendations,
    report?.content?.recommendations,
  ])
  if (primary.length) return primary

  const fallbackSingle = normalizeReportList([
    report?.content?.self_care_tip,
    report?.content?.suggestion,
    report?.content?.encouragement,
    report?.content?.professional_note,
  ])
  if (fallbackSingle.length) return fallbackSingle

  return firstNonEmptyList([
    report?.content?.concerns,
    report?.content?.growth_areas,
  ])
}

function normalizeScaleScore(value, scale) {
  if (value == null || typeof value === 'boolean' || (typeof value === 'string' && !value.trim())) return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  const scaled = num * (100 / scale)
  return Math.min(100, Math.max(0, Math.round(scaled)))
}

export function extractStructuredReportDimensions(report) {
  const content = report?.content
  if (!content || typeof content !== 'object') return []

  const mapped = [
    { id: 'communication_quality', label: '沟通质量', scale: 10, raw: content.communication_quality?.score ?? content.communication_quality },
    { id: 'emotional_sync', label: '情绪同步', scale: 100, raw: content.emotional_sync?.score ?? content.emotional_sync },
    { id: 'interaction_balance', label: '互动平衡', scale: 100, raw: content.interaction_balance?.score ?? content.interaction_balance },
    { id: 'mood_a', label: '一方情绪', scale: 10, raw: content.mood_a?.score ?? content.mood_a },
    { id: 'mood_b', label: '另一方情绪', scale: 10, raw: content.mood_b?.score ?? content.mood_b },
  ]
    .map((item) => ({ id: item.id, label: item.label, score: normalizeScaleScore(item.raw, item.scale) }))
    .filter((item) => item.score !== null)

  return mapped.length >= 3 ? mapped : []
}

export function reportHasDisplayContent(report) {
  return Boolean(
    report && (
      report.status === 'completed'
      || report.content
      || report.summary
    ),
  )
}

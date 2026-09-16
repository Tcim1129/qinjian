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

export function extractReportInsights(report) {
  return firstNonEmptyList([
    report?.content?.highlights,
    report?.content?.weekly_highlights,
    report?.content?.strengths,
    report?.key_insights,
    report?.evidence_summary,
  ])
}

export function extractReportRecommendations(report) {
  return firstNonEmptyList([
    report?.content?.action_plan,
    report?.content?.next_month_goals,
    report?.recommendations,
    report?.content?.recommendations,
    report?.content?.concerns,
    report?.content?.growth_areas,
  ])
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

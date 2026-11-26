export const MAX_CHECKIN_BACKFILL_DAYS = 30

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export function formatLocalDateKey(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function shiftDateKey(baseDateKey, deltaDays = 0) {
  const key = ISO_DATE_PATTERN.test(String(baseDateKey || ''))
    ? String(baseDateKey)
    : formatLocalDateKey()
  const [year, month, day] = key.split('-').map(Number)
  const shifted = new Date(Date.UTC(year, month - 1, day + Number(deltaDays || 0)))
  return shifted.toISOString().slice(0, 10)
}

export function getCheckinDateBounds(todayKey = formatLocalDateKey(), maxDays = MAX_CHECKIN_BACKFILL_DAYS) {
  const safeToday = ISO_DATE_PATTERN.test(String(todayKey || '')) ? String(todayKey) : formatLocalDateKey()
  return {
    min: shiftDateKey(safeToday, -Math.max(0, Number(maxDays) || 0)),
    max: safeToday,
  }
}

export function clampCheckinDate(value, todayKey = formatLocalDateKey(), maxDays = MAX_CHECKIN_BACKFILL_DAYS) {
  const bounds = getCheckinDateBounds(todayKey, maxDays)
  const candidate = String(value || '').trim()
  if (!ISO_DATE_PATTERN.test(candidate)) return bounds.max
  const [y, m, d] = candidate.split('-').map(Number)
  const parsed = new Date(Date.UTC(y, m - 1, d))
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== candidate) {
    return bounds.max
  }
  if (candidate > bounds.max) return bounds.max
  if (candidate < bounds.min) return bounds.min
  return candidate
}

export function describeCheckinDate(dateKey, todayKey = formatLocalDateKey()) {
  const safeToday = ISO_DATE_PATTERN.test(String(todayKey || '')) ? String(todayKey) : formatLocalDateKey()
  const normalized = clampCheckinDate(dateKey, safeToday)
  if (normalized === safeToday) return '今天'
  if (normalized === shiftDateKey(safeToday, -1)) return '昨天'
  if (normalized === shiftDateKey(safeToday, -2)) return '前天'
  const [, month, day] = normalized.split('-')
  return `${Number(month)}月${Number(day)}日`
}

export function normalizeManualCheckinContent({ content = '', imageAnalysisSummary = '' } = {}) {
  const normalizedContent = String(content || '').trim()
  if (normalizedContent) return normalizedContent

  const normalizedImageSummary = String(imageAnalysisSummary || '').trim()
  return normalizedImageSummary ? `图片记录：${normalizedImageSummary}` : ''
}

export function getMissingBackgroundFields() {
  return []
}

export function getManualCheckinValidation({
  content = '',
  imageAnalysisSummary = '',
} = {}) {
  const normalizedManualContent = normalizeManualCheckinContent({
    content,
    imageAnalysisSummary,
  })

  return {
    normalizedManualContent,
    missingBackgroundFields: [],
    isBackgroundComplete: true,
    canSubmitManualCheckin: Boolean(normalizedManualContent),
  }
}

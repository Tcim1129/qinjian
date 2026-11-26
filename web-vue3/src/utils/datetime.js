const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/
const OFFSET_RE = /(Z|[+-]\d{2}:?\d{2})$/i
const BEIJING_TIMEZONE = 'Asia/Shanghai'

function pad2(value) {
  return String(value).padStart(2, '0')
}

function formatParts(date, options) {
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: BEIJING_TIMEZONE,
      hour12: false,
      ...options,
    })
      .formatToParts(date)
      .map((part) => [part.type, part.value])
  )
}

/**
 * 解析服务端返回的时间字符串。
 * 后端以无时区后缀的 UTC 时间序列化（如 "2026-11-25T08:30:00"），
 * 补齐 Z 后按 UTC 解析，避免浏览器将其误判为本地时间导致 8 小时偏差。
 */
export function parseServerDateTime(value) {
  if (!value) return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  if (typeof value === 'number') {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? null : date
  }
  const raw = String(value).trim()
  if (!raw) return null
  if (DATE_ONLY_RE.test(raw)) {
    const date = new Date(`${raw}T00:00:00+08:00`)
    return Number.isNaN(date.getTime()) ? null : date
  }
  const isoLike = raw.includes(' ') && !raw.includes('T') ? raw.replace(' ', 'T') : raw
  const normalized = OFFSET_RE.test(isoLike) ? isoLike : `${isoLike}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function getServerTimestampMs(value) {
  const date = parseServerDateTime(value)
  return date ? date.getTime() : Number.NaN
}

export function formatBeijingMonthDayTime(value, { padDate = false } = {}) {
  const date = parseServerDateTime(value)
  if (!date) return ''
  const parts = formatParts(date, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
  const month = padDate ? parts.month : String(Number(parts.month))
  const day = padDate ? parts.day : String(Number(parts.day))
  const hour = parts.hour === '24' ? '00' : parts.hour
  return `${month}-${day} ${hour}:${parts.minute}`
}

export function formatBeijingDate(value) {
  if (!value) return ''
  const raw = String(value).trim()
  const dateOnly = raw.match(DATE_ONLY_RE)
  if (dateOnly) return `${dateOnly[1]}-${dateOnly[2]}-${dateOnly[3]}`
  const date = parseServerDateTime(raw)
  if (!date) return ''
  const parts = formatParts(date, { year: 'numeric', month: '2-digit', day: '2-digit' })
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function formatBeijingShortDate(value) {
  if (!value) return ''
  const raw = String(value).trim()
  const dateOnly = raw.match(DATE_ONLY_RE)
  if (dateOnly) return `${Number(dateOnly[2])}月${Number(dateOnly[3])}日`
  const date = parseServerDateTime(raw)
  if (!date) return ''
  const parts = formatParts(date, { month: 'numeric', day: 'numeric' })
  return `${Number(parts.month)}月${Number(parts.day)}日`
}

export function formatBeijingDateTime(value) {
  const date = parseServerDateTime(value)
  if (!date) return ''
  const parts = formatParts(date, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
  const hour = parts.hour === '24' ? '00' : parts.hour
  return `${parts.year}-${parts.month}-${parts.day} ${hour}:${parts.minute}`
}

export function formatBeijingTime(value) {
  const date = parseServerDateTime(value)
  if (!date) return ''
  const parts = formatParts(date, { hour: '2-digit', minute: '2-digit' })
  const hour = parts.hour === '24' ? '00' : parts.hour
  return `${pad2(hour)}:${pad2(parts.minute)}`
}

const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const OFFSET_PATTERN = /(Z|[+-]\d{2}:?\d{2})$/i

function pad(value) {
  return String(value).padStart(2, '0')
}

function dateKeyFromParts(parts) {
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

export function validDateKey(value) {
  const text = String(value || '').trim()
  if (!DATE_ONLY_PATTERN.test(text)) return ''
  const date = new Date(`${text}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === text ? text : ''
}

export function parseTimelineInstant(value) {
  const text = String(value || '').trim()
  if (!text || DATE_ONLY_PATTERN.test(text) || !validDateKey(text.slice(0, 10))) return null
  const normalized = OFFSET_PATTERN.test(text) ? text : `${text}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function timelineBusinessDateKey(value, timeZone = 'Asia/Shanghai') {
  if (value && typeof value === 'object') {
    const localDate = String(value.local_date || '').trim()
    if (localDate) return validDateKey(localDate)
    return timelineBusinessDateKey(value.occurred_at || value.created_at || value.timestamp, timeZone)
  }

  const text = String(value || '').trim()
  if (DATE_ONLY_PATTERN.test(text)) return validDateKey(text)
  const date = parseTimelineInstant(text)
  if (!date) return ''
  return dateKeyFromParts(new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date))
}

export function localDateKey(date = new Date()) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function buildCalendarDays(year, monthIndex, eventMap = new Map(), todayKey = localDateKey()) {
  const first = new Date(year, monthIndex, 1)
  const last = new Date(year, monthIndex + 1, 0)
  const start = new Date(year, monthIndex, 1 - first.getDay())
  const end = new Date(year, monthIndex, last.getDate() + (6 - last.getDay()))
  const days = []

  for (const cursor = new Date(start); cursor <= end; cursor.setDate(cursor.getDate() + 1)) {
    const key = localDateKey(cursor)
    days.push({
      key,
      day: cursor.getDate(),
      isCurrentMonth: cursor.getMonth() === monthIndex,
      isToday: key === todayKey,
      eventCount: eventMap.get(key)?.length || 0,
    })
  }
  return days
}

function entityKey(item) {
  const sourceId = String(item?.entity_id || item?.id || '').trim()
  const rawType = String(item?.entity_type || item?.item_type || '').trim()
  const sourceType = ['record', 'partner_record_placeholder'].includes(rawType) ? 'checkin' : rawType
  return sourceId ? `${sourceType}:${sourceId}` : ''
}

function normalizeArchiveItem(item) {
  return {
    ...item,
    source: 'archive',
    entity_type: item?.item_type,
    entity_id: item?.id,
    label: item?.item_type === 'report' ? '关系简报' : '关系记录',
    detail: item?.summary || '',
    category_label: '档案',
    tone: 'neutral',
    tone_label: item?.item_type === 'partner_record_placeholder' ? '仅共享摘要' : '已归档',
  }
}

// The fixture timestamps describe local Chinese time, unlike naive UTC API timestamps.
export function buildDemoTimelineEvents(fixture, pairId) {
  const localTimestamp = value => value ? value + (OFFSET_PATTERN.test(value) ? '' : '+08:00') : ''
  const events = (fixture.timelineEvents || []).filter(item => item.pair_id === pairId).map(item => ({
    id: item.id, pair_id: item.pair_id, entity_id: item.id, entity_type: 'relationship_event',
    occurred_at: localTimestamp(item.timestamp), label: '关系记录', title: item.title,
    summary: item.title, detail: item.description, tags: item.tags,
  }))
  const alignment = fixture.narrativeAlignments?.[pairId] || fixture.narrativeAlignment
  if (alignment?.pair_id === pairId) events.push({
    id: alignment.event_id, pair_id: pairId, entity_id: alignment.event_id, entity_type: 'narrative_alignment',
    local_date: alignment.checkin_date, occurred_at: localTimestamp(alignment.generated_at || (alignment.checkin_date ? alignment.checkin_date + 'T20:00:00' : '')),
    label: '双视角分析', title: '这一天的双视角分析', summary: alignment.shared_story,
    detail: alignment.coach_note, tags: ['双视角', '样例分析'],
  })
  return events
}

export function mergeTimelineItems(events = [], archiveItems = []) {
  const merged = []
  const seen = new Set()
  const seenEventIds = new Set()
  for (const item of events) {
    if (item.id && seenEventIds.has(item.id)) continue
    if (item.id) seenEventIds.add(item.id)
    const normalized = { ...item, source: 'event' }
    const key = entityKey(normalized)
    if (key) seen.add(key)
    merged.push(normalized)
  }
  for (const item of archiveItems) {
    const normalized = normalizeArchiveItem(item)
    const key = entityKey(normalized)
    if (key && seen.has(key)) {
      const matching = merged.find(candidate => entityKey(candidate) === key && candidate.source === 'event')
      if (matching) Object.assign(matching, {
        local_date: normalized.local_date,
        record: normalized.record,
        report: normalized.report,
        locked_reason: normalized.locked_reason,
        visibility: normalized.visibility,
      })
      continue
    }
    if (key) seen.add(key)
    merged.push(normalized)
  }
  return merged.sort((left, right) => {
    const leftTime = parseTimelineInstant(left?.occurred_at)?.getTime() || 0
    const rightTime = parseTimelineInstant(right?.occurred_at)?.getTime() || 0
    return rightTime - leftTime
  })
}

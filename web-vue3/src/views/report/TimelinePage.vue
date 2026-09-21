<template>
  <div class="timeline-page">
    <header class="page-head page-head--split">
      <h2>关系日历</h2>
      <div class="page-head__aside">
        <button class="btn btn-ghost" type="button" @click="openReportPage">查看简报</button>
        <button class="btn btn-primary" type="button" :disabled="loadingEvents" @click="handleRefresh">刷新</button>
      </div>
    </header>
    <div class="timeline-meta">
      <span>{{ pairName }}<span v-if="experienceMode.isDemoMode" class="sample-label"> · 样例</span></span>
    </div>
    <p v-if="loadError" class="timeline-error" role="alert">{{ loadError }}</p>

    <section class="timeline-workspace">
      <article class="calendar-card">
        <div class="calendar-head">
          <h3 aria-live="polite">{{ monthLabel }}</h3>
          <div class="calendar-actions">
            <button class="calendar-nav" type="button" aria-label="上个月" @click="changeMonth(-1)">‹</button>
            <button class="calendar-today" type="button" @click="goToday">今天</button>
            <button class="calendar-nav" type="button" aria-label="下个月" @click="changeMonth(1)">›</button>
          </div>
        </div>
        <div class="calendar-weekdays" aria-hidden="true"><span v-for="day in weekdays" :key="day">{{ day }}</span></div>
        <div class="calendar-grid" role="group" :aria-label="monthLabel + '，选择日期'">
          <button v-for="day in calendarDays" :key="day.key" type="button" class="calendar-day"
            :class="{ 'is-outside': !day.isCurrentMonth, 'is-today': day.isToday, 'is-selected': day.key === selectedDateKey }"
            :aria-label="day.key + (day.eventCount ? '，' + day.eventCount + ' 条记录' : '，未找到记录')"
            :aria-pressed="day.key === selectedDateKey" :aria-current="day.isToday ? 'date' : undefined"
            @click="selectDate(day.key)" @keydown="onCalendarKey($event, day.key)">
            <span>{{ day.day }}</span><i v-if="day.eventCount" class="calendar-dot" aria-hidden="true"></i>
          </button>
        </div>
        <div class="calendar-legend"><i class="calendar-dot" aria-hidden="true"></i><span>有记录</span></div>
        <div v-if="!experienceMode.isDemoMode" class="calendar-range">
          <button v-if="archiveNextBefore" class="btn btn-ghost btn-sm" type="button" :disabled="loadingOlder || loadingEvents" @click="loadOlderArchive">{{ loadingOlder ? '加载中…' : '查看更多记录' }}</button>
          <details><summary>记录范围</summary><p>已加载 {{ timelineItems.length }} 条，按北京时间显示。日历只标记已加载的内容；记录和报告可以继续向前查，其他事件只显示最近 60 条。</p></details>
        </div>
      </article>

      <article class="day-records" :aria-busy="loadingEvents">
        <header class="day-records-head"><h3>{{ selectedDateLabel }}</h3><span>{{ selectedDayItems.length }} 条</span></header>
        <div v-if="loadingEvents && !timelineItems.length" class="timeline-empty" role="status">加载中…</div>
        <ol v-else-if="selectedDayItems.length" class="day-records-list">
          <li v-for="event in selectedDayItems" :key="event.source + '-' + event.id">
            <button type="button" class="record-button" @click="openEventDetail(event)">
              <span class="record-top"><span>{{ event.label || '关系记录' }}</span><time>{{ formatTime(event.occurred_at) }}</time></span>
              <strong>{{ event.title || event.summary || '记录详情' }}</strong>
              <span v-if="event.detail && event.detail !== (event.title || event.summary)" class="record-excerpt">{{ event.detail }}</span>
              <span class="record-bottom"><span>{{ event.tags?.slice(0, 2).join(' · ') }}</span><span>详情 ↗</span></span>
            </button>
          </li>
        </ol>
        <div v-else class="timeline-empty">
          <span class="empty-day" aria-hidden="true">{{ selectedDateKey.slice(-2) }}</span>
          <strong>暂未找到当天记录</strong>
          <p v-if="loadError || archiveNextBefore">{{ loadError ? '部分记录加载失败，请刷新重试。' : '还有更早的记录未加载。' }}</p>
        </div>
        <button v-if="selectedDayItems.length" class="day-agent-button" type="button" @click="openAgentForDay"><span>和 AI 聊聊这一天</span><span aria-hidden="true">↗</span></button>
      </article>
    </section>

    <dialog ref="detailDialog" class="timeline-detail" aria-labelledby="timeline-detail-title" @cancel.prevent="closeDetail" @close="resetDetail">
      <header class="timeline-detail-head"><div><p class="eyebrow">{{ detailDateLabel }} · {{ detailItem?.label }}{{ experienceMode.isDemoMode ? ' · 样例' : '' }}</p><h3 id="timeline-detail-title">{{ detailTitle }}</h3></div><button class="btn btn-ghost btn-sm" type="button" aria-label="关闭详情" @click="closeDetail">关闭</button></header>
      <div class="timeline-detail-body">
        <p v-if="detailSummary && detailSummary !== detailTitle" class="detail-summary">{{ detailSummary }}</p>
        <p v-if="detailItem?.detail && detailItem.detail !== detailSummary">{{ detailItem.detail }}</p>
        <p v-if="detailLoading" role="status">详情加载中…</p>
        <p v-if="detailError" class="timeline-error" role="alert">{{ detailError }} <button class="text-button" type="button" @click="loadDetail">重试</button></p>
        <p v-if="detailItem?.locked_reason" class="detail-note">{{ detailItem.locked_reason }}</p>
        <dl v-if="detailMetrics.length" class="detail-metrics"><div v-for="metric in detailMetrics" :key="metric.label"><dt>{{ metric.label }}</dt><dd>{{ metric.value ?? '暂无' }}</dd></div></dl>
        <section v-for="(card, index) in detailCards" :key="index" class="detail-evidence"><h4>{{ card.title }}</h4><p>{{ card.body }}</p></section>
        <p v-if="detailData?.recommended_next_action" class="detail-next">建议：{{ detailData.recommended_next_action }}</p>
      </div>
      <footer class="timeline-detail-footer"><button class="btn btn-ghost" type="button" @click="closeDetail">返回</button><button class="btn btn-primary" type="button" @click="openAgentForDetail">和 AI 聊聊这件事</button></footer>
    </dialog>
    <ContextAgentDialog v-if="agentContext" :context="agentContext" @close="agentContext = null" />
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { demoFixture } from '@/demo/fixtures'
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { buildPairQuery, resolveScopedPairId } from '@/utils/reportScopeSelection'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'
import { buildCalendarDays, buildDemoTimelineEvents, mergeTimelineItems, parseTimelineInstant, timelineBusinessDateKey, validDateKey } from '@/utils/timelineCalendar'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const notify = inject('showToast', () => {})
const pairId = computed(() => resolveScopedPairId({ preferredPairId: route.query.pair_id, fallbackPairId: userStore.activePairId, availablePairs: (userStore.pairs || []).filter(p => p.status === 'active').map(p => p.id) }) || null)
const pairName = computed(() => userStore.pairs.find(p => p.id === pairId.value)?.partner_nickname || (pairId.value ? '当前关系' : '我的记录'))
const experienceMode = computed(() => resolveExperienceMode({ isDemoMode: userStore.isDemoMode, activePairId: pairId.value, pairs: userStore.pairs }))
const todayKey = () => timelineBusinessDateKey(new Date().toISOString())
const selectedDateKey = ref(validDateKey(route.query.date) || todayKey())
const displayedMonth = ref(selectedDateKey.value.slice(0, 7))
const timelineEvents = ref([])
const archiveItems = ref([])
const archiveNextBefore = ref(null)
const loadingEvents = ref(false)
const loadingOlder = ref(false)
const loadError = ref('')
const detailDialog = ref(null)
const detailItem = ref(null)
const detailData = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const agentContext = ref(null)
let scopeVersion = 0
let detailVersion = 0
let disposed = false
let userSelectedDate = Boolean(validDateKey(route.query.date))
let returnFocus = null
const refreshGuard = createRefreshAttemptGuard({ maxAttempts: 3, windowMs: 60000 })

const timelineItems = computed(() => mergeTimelineItems(timelineEvents.value, archiveItems.value))
const eventsByDate = computed(() => {
  const map = new Map()
  for (const item of timelineItems.value) {
    const key = timelineBusinessDateKey(item)
    if (key) map.set(key, [...(map.get(key) || []), item])
  }
  return map
})
const calendarDays = computed(() => {
  const [year, month] = displayedMonth.value.split('-').map(Number)
  return buildCalendarDays(year, month - 1, eventsByDate.value, todayKey())
})
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const monthLabel = computed(() => { const [year, month] = displayedMonth.value.split('-'); return year + '年' + Number(month) + '月' })
const selectedDateLabel = computed(() => formatDate(selectedDateKey.value))
const selectedDayItems = computed(() => eventsByDate.value.get(selectedDateKey.value) || [])
const detailTitle = computed(() => detailItem.value?.title || detailItem.value?.summary || '记录详情')
const detailDateLabel = computed(() => formatDate(timelineBusinessDateKey(detailItem.value)))
const detailSummary = computed(() => detailData.value?.event_summary || detailItem.value?.summary || '')
const detailMetrics = computed(() => detailData.value?.metrics || (detailItem.value?.record ? [{ label: '心情', value: detailItem.value.record.mood_score }] : []))
const detailCards = computed(() => {
  const cards = [...(detailData.value?.evidence_cards || [])]
  const record = detailItem.value?.record
  if (record?.content && !cards.some(card => card.body === record.content)) cards.unshift({ title: '当时的记录', body: record.content })
  for (const text of detailItem.value?.report?.recommendations || []) cards.push({ title: '报告建议', body: String(text) })
  return cards
})

function formatDate(key) { if (!validDateKey(key)) return ''; const [year, month, day] = key.split('-'); return year + '年' + Number(month) + '月' + Number(day) + '日' }
function formatTime(value) {
  const date = parseTimelineInstant(value)
  return date ? new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false }).format(date) : ''
}
function openReportPage() { router.push({ path: '/report', query: buildPairQuery(pairId.value) }) }
function selectDate(key) { if (!validDateKey(key)) return; userSelectedDate = true; selectedDateKey.value = key; displayedMonth.value = key.slice(0, 7) }
function changeMonth(offset) {
  const [year, month] = displayedMonth.value.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1 + offset, 1))
  selectDate(date.toISOString().slice(0, 10))
}
function goToday() { selectDate(todayKey()) }
async function onCalendarKey(event, key) {
  const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key]
  if (!offset) return
  event.preventDefault()
  const calendar = event.currentTarget?.closest('.calendar-grid')
  const date = new Date(key + 'T00:00:00Z')
  date.setUTCDate(date.getUTCDate() + offset)
  const nextKey = date.toISOString().slice(0, 10)
  selectDate(nextKey)
  await nextTick()
  calendar?.querySelector('[aria-pressed="true"]')?.focus()
}
function normalizeEvent(event) {
  const payload = event.payload || {}
  return { ...event, label: payload.event_label || event.label || '关系事件', summary: event.summary || payload.summary || '留下一条记录' }
}
function selectInitialDate() {
  if (userSelectedDate || eventsByDate.value.has(selectedDateKey.value)) return
  const latestKey = [...eventsByDate.value.keys()].sort().at(-1)
  if (latestKey) { selectedDateKey.value = latestKey; displayedMonth.value = latestKey.slice(0, 7) }
}
async function refreshTimeline() {
  const version = ++scopeVersion
  const scopedPair = pairId.value
  loadingEvents.value = true
  loadingOlder.value = false
  loadError.value = ''
  archiveNextBefore.value = null
  closeDetail()
  agentContext.value = null
  try {
    if (experienceMode.value.isDemoMode) {
      timelineEvents.value = buildDemoTimelineEvents(demoFixture, scopedPair)
      archiveItems.value = []
      selectInitialDate()
      return
    }
    const [events, archive] = await Promise.allSettled([api.getRelationshipTimeline(scopedPair, 60), api.getTimelineArchive(scopedPair, { limit: 60 })])
    if (disposed || version !== scopeVersion) return
    timelineEvents.value = events.status === 'fulfilled' ? (events.value?.events || []).map(normalizeEvent) : []
    archiveItems.value = archive.status === 'fulfilled' ? archive.value?.items || [] : []
    archiveNextBefore.value = archive.status === 'fulfilled' ? archive.value?.next_before || null : null
    const errors = []
    if (events.status === 'rejected') errors.push('近期事件暂时没有加载出来')
    if (archive.status === 'rejected') errors.push('历史记录暂时没有加载出来')
    loadError.value = errors.length ? errors.join('；') + '，可以刷新重试。' : ''
    selectInitialDate()
  } finally {
    if (!disposed && version === scopeVersion) loadingEvents.value = false
  }
}
function handleRefresh() {
  const seconds = refreshGuard.getRemainingSeconds()
  if (seconds) return notify('刷新得有点频繁，请 ' + seconds + ' 秒后再试')
  refreshGuard.markRun()
  return refreshTimeline()
}
async function loadOlderArchive() {
  if (loadingOlder.value || loadingEvents.value || !archiveNextBefore.value || experienceMode.value.isDemoMode) return
  const version = scopeVersion
  const before = archiveNextBefore.value
  loadingOlder.value = true
  try {
    const response = await api.getTimelineArchive(pairId.value, { before, limit: 60 })
    if (disposed || version !== scopeVersion) return
    archiveItems.value = [...archiveItems.value, ...(response?.items || [])]
    archiveNextBefore.value = response?.next_before && response.next_before !== before ? response.next_before : null
  } catch (error) {
    if (!disposed && version === scopeVersion) notify(error.message || '更早记录没能加载，请重试')
  } finally {
    if (!disposed && version === scopeVersion) loadingOlder.value = false
  }
}
async function openEventDetail(item) {
  returnFocus = document.activeElement
  detailItem.value = item
  detailData.value = null
  detailError.value = ''
  await nextTick()
  if (!detailItem.value || disposed) return
  detailDialog.value?.showModal()
  if (item.source === 'event' && !experienceMode.value.isDemoMode) void loadDetail()
}
async function loadDetail() {
  if (!detailItem.value) return
  const version = ++detailVersion
  const eventId = detailItem.value.id
  detailLoading.value = true
  detailError.value = ''
  try {
    const response = await api.getTimelineEventDetail(eventId)
    if (!disposed && version === detailVersion) detailData.value = response
  } catch (error) {
    if (!disposed && version === detailVersion) detailError.value = error.message || '更多详情暂时没有加载出来。'
  } finally {
    if (!disposed && version === detailVersion) detailLoading.value = false
  }
}
function resetDetail() { detailVersion++; detailItem.value = null; detailData.value = null; detailError.value = ''; detailLoading.value = false }
function closeDetail() { detailDialog.value?.close(); resetDetail(); returnFocus?.focus?.(); returnFocus = null }
function openAgentForDay() {
  const records = selectedDayItems.value.slice(0, 6).map(item => (item.title || item.summary) + (item.detail && item.detail !== item.summary ? '：' + item.detail : ''))
  agentContext.value = { title: '聊聊这一天', sourceLabel: selectedDateLabel.value + (selectedDayItems.value.length > 6 ? ' · 节选 6 条' : '') + (experienceMode.value.isDemoMode ? ' · 样例' : ''), summary: records.join('\n'), question: '帮我看看这一天发生的事，接下来可以做些什么？先给一个简单的建议就好。', pairId: pairId.value }
}
function openAgentForDetail() {
  const context = { title: '聊聊这件事', sourceLabel: detailDateLabel.value + ' · ' + (detailItem.value?.label || '记录') + (experienceMode.value.isDemoMode ? ' · 样例' : ''), summary: [detailSummary.value, detailItem.value?.detail].filter(Boolean).filter((value, index, items) => items.indexOf(value) === index).join('\n'), question: '帮我理一理这件事，哪些地方还需要问清楚？', pairId: pairId.value }
  closeDetail()
  agentContext.value = context
}
watch(() => [pairId.value, userStore.token, userStore.me?.id], () => {
  scopeVersion++
  timelineEvents.value = []
  archiveItems.value = []
  archiveNextBefore.value = null
  userSelectedDate = Boolean(validDateKey(route.query.date))
  selectedDateKey.value = validDateKey(route.query.date) || todayKey()
  displayedMonth.value = selectedDateKey.value.slice(0, 7)
  void refreshTimeline()
}, { flush: 'sync' })
watch(() => route.query.date, value => { closeDetail(); agentContext.value = null; if (validDateKey(value)) selectDate(value) })
onMounted(refreshTimeline)
onBeforeUnmount(() => { disposed = true; scopeVersion++; closeDetail() })
</script>

<style scoped>
.timeline-page { width: min(var(--content-max), calc(100% - 32px)); margin: 0 auto; padding-bottom: 40px; }
.timeline-page .page-head { width: 100%; padding-bottom: 12px; }
.timeline-meta { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; margin: 0 0 18px; color: var(--ink-soft); font-size: 13px; }
.sample-label { color: #886036; font-size: 13px; }
.timeline-workspace { display: grid; grid-template-columns: minmax(310px, .85fr) minmax(0, 1.15fr); gap: 24px; align-items: start; }
.calendar-card { padding: 24px; border: 1px solid var(--border-strong); border-radius: 18px; background: #fffaf4; position: sticky; top: 90px; }
.calendar-head, .calendar-actions, .day-records-head, .record-top, .record-bottom, .day-agent-button, .timeline-detail-head, .timeline-detail-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.calendar-head { margin-bottom: 24px; }
.calendar-head h3 { font-size: 21px; margin: 0; font-family: var(--font-serif); }
.calendar-actions { gap: 4px; }
.calendar-nav, .calendar-today { background: transparent; border: 0; color: var(--ink-soft); cursor: pointer; min-height: 36px; padding: 4px 9px; border-radius: 8px; }
.calendar-nav { font-size: 26px; }
.calendar-today { font-size: 12px; }
.calendar-nav:hover, .calendar-today:hover { background: #f0e5d8; }
.calendar-weekdays, .calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
.calendar-weekdays { text-align: center; font-size: 12px; color: var(--ink-soft); margin-bottom: 12px; }
.calendar-day { display: flex; position: relative; flex-direction: column; justify-content: center; align-items: center; aspect-ratio: 1; min-height: 38px; background: transparent; color: var(--ink); border: 1px solid transparent; border-radius: 50%; cursor: pointer; font: inherit; font-variant-numeric: tabular-nums; }
.calendar-day:hover { background: #f0e5d8; }
.calendar-day.is-outside { color: #9c9489; opacity: .65; }
.calendar-day.is-today { border-color: var(--seal); }
.calendar-day.is-selected { color: white; background: var(--seal-deep, #ac4f38); opacity: 1; }
.calendar-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--seal); flex-shrink: 0; }
.calendar-day .calendar-dot { position: absolute; bottom: 13%; }
.calendar-day.is-selected .calendar-dot { background: white; }
.calendar-legend { display: flex; align-items: center; gap: 8px; margin-top: 20px; font-size: 12px; color: var(--ink-soft); }
.calendar-range { border-top: 1px solid var(--border); margin-top: 16px; padding-top: 14px; }
.calendar-range p { margin: 10px 0 0; font-size: 12px; line-height: 1.65; color: var(--ink-soft); }
.calendar-range details { margin-top: 10px; color: var(--ink-soft); font-size: 12px; }
.calendar-range summary { cursor: pointer; }
.day-records { min-width: 0; }
.day-records-head { padding: 2px 0 18px; border-bottom: 1px solid var(--border-strong); margin-bottom: 18px; }
.day-records-head h3 { font: 24px var(--font-serif); margin: 0; }
.day-records-head > span { font-size: 13px; color: var(--ink-soft); }
.day-records-list { margin: 0; padding: 0; list-style: none; display: grid; gap: 14px; }
.record-button { width: 100%; text-align: left; display: grid; gap: 12px; padding: 22px; border: 1px solid var(--border); border-radius: 14px; background: #fffdf9; cursor: pointer; color: var(--ink); font: inherit; transition: border-color .15s, transform .15s; overflow-wrap: anywhere; }
.record-button:hover { border-color: var(--seal); transform: translateY(-2px); }
.record-top { color: var(--seal-deep); font-size: 12px; }
.record-top time, .record-bottom { color: var(--ink-soft); }
.record-button strong { font-size: 19px; line-height: 1.55; font-weight: 600; }
.record-excerpt { color: var(--ink-soft); font-size: 14px; line-height: 1.75; }
.record-bottom { font-size: 12px; margin-top: 2px; }
.record-bottom > span:last-child { color: var(--seal-deep); white-space: nowrap; }
.day-agent-button { width: 100%; border: 0; border-top: 1px solid var(--border-strong); margin-top: 22px; padding: 18px 2px; color: var(--seal-deep); cursor: pointer; background: transparent; text-align: left; font: inherit; }
.timeline-empty { min-height: 255px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; color: var(--ink-soft); padding: 20px; }
.timeline-empty p { font-size: 13px; margin: 0; line-height: 1.7; }
.empty-day { font: 56px var(--font-serif); color: #b7a797; }
.timeline-error { padding: 12px 16px; background: #fbede5; color: #88422f; border-radius: 10px; font-size: 13px; line-height: 1.7; }
.timeline-detail { width: min(680px, calc(100vw - 32px)); max-height: calc(100dvh - 40px); margin: auto; padding: 0; background: #fffcf7; color: var(--ink); border: 1px solid var(--border-strong); border-radius: 18px; overflow: auto; }
.timeline-detail::backdrop { background: #29201770; }
.timeline-detail-head { padding: 24px; align-items: flex-start; border-bottom: 1px solid var(--border); }
.timeline-detail-head h3 { margin: 0; font: 24px/1.4 var(--font-serif); overflow-wrap: anywhere; }
.timeline-detail-head button { flex-shrink: 0; }
.timeline-detail-body { padding: 20px 24px; line-height: 1.85; overflow-wrap: anywhere; }
.detail-summary { margin-top: 0; }
.detail-metrics { display: flex; gap: 24px; flex-wrap: wrap; }
.detail-metrics dt { color: var(--ink-soft); font-size: 12px; }
.detail-metrics dd { margin: 0; }
.detail-evidence { border-top: 1px solid var(--border); padding-top: 14px; margin-top: 16px; }
.detail-evidence h4 { margin: 0; font-size: 14px; }
.detail-evidence p { white-space: pre-wrap; }
.detail-note { color: var(--ink-soft); font-size: 13px; }
.detail-next { background: #f5ede1; padding: 12px; border-radius: 8px; }
.timeline-detail-footer { padding: 16px 24px; border-top: 1px solid var(--border); background: #fffcf7; position: sticky; bottom: 0; }
.text-button { color: inherit; background: transparent; border: 0; text-decoration: underline; cursor: pointer; }
button:focus-visible { outline: 3px solid var(--seal); outline-offset: 3px; }
@media (max-width: 800px) { .timeline-workspace { grid-template-columns: 1fr; gap: 26px; } .calendar-card { position: static; } .calendar-grid { gap: 8px; } .calendar-day { max-height: 54px; aspect-ratio: auto; height: 46px; border-radius: 10px; } }
@media (max-width: 500px) { .timeline-page { width: calc(100% - 24px); } .calendar-card { padding: 18px; } .calendar-head { gap: 4px; } .calendar-actions { gap: 0; } .calendar-day { min-height: 36px; height: 40px; } .record-button { padding: 18px; } .timeline-detail-head, .timeline-detail-body { padding: 18px; } .timeline-detail-footer { padding: 14px; } }
@media (prefers-reduced-motion: reduce) { .record-button { transition: none; } }
</style>

<template>
  <div class="report-page page-stack">
    <div class="report-hero">
      <div class="report-hero__copy">
        <p class="eyebrow">简报</p>
        <h2>看看最近相处得怎么样</h2>
      </div>
      <button class="btn btn-primary report-refresh" type="button" :disabled="generating || loading" @click="generateReport">
        {{ generating ? '生成中…' : isDemoMode ? '刷新样例' : '刷新' }}
      </button>
    </div>

    <section class="report-scope-card">
      <div class="segmented report-tabs">
        <button :class="{ active: reportStore.reportType === 'daily' }" type="button" @click="switchType('daily')">日报</button>
        <button :class="{ active: reportStore.reportType === 'weekly' }" :disabled="!isDemoMode && !selectedPairId" type="button" @click="switchType('weekly')">周报</button>
        <button :class="{ active: reportStore.reportType === 'monthly' }" :disabled="!isDemoMode && !selectedPairId" type="button" @click="switchType('monthly')">月报</button>
      </div>

      <div class="report-scope-selector">
        <label for="report-pair">查看关系</label>
        <select id="report-pair" v-model="selectedPairId" class="report-scope-selector__button" @change="changeReportPair">
          <option v-if="!isDemoMode" value="">个人记录</option>
          <option v-for="pair in availableReportPairs" :key="pair.id" :value="pair.id">{{ partnerName(pair) }} · {{ pairTypeLabel(pair) }}</option>
        </select>
      </div>
    </section>

    <p v-if="!isDemoMode && !selectedPairId" class="report-personal-note">个人记录目前仅支持日报</p>
    <p v-if="notice" role="status">{{ notice }}</p>

    <article v-if="displayReport" class="report-paper">
      <header class="report-paper__head">
        <div class="report-paper__intro">
          <div class="report-meta">
            <span>{{ reportTypeLabel(displayReport.report_type) }}</span>
            <span>{{ displayReport.date_label }}</span>
            <span>{{ displayReport.relation_label }}</span>
          </div>
          <h3>{{ displayReport.summary }}</h3>
          <div class="report-chips">
            <span v-for="tag in displayReport.tags" :key="tag" class="report-chip">{{ tag }}</span>
            <button
              v-for="link in displayReport.quick_links"
              :key="link"
              class="report-chip report-chip--action"
              type="button"
              @click="openQuickLink(link)"
            >
              {{ link }}
            </button>
          </div>
        </div>

        <div class="report-score">
          <span>{{ displayReport.health_score }}</span>
          <small>{{ displayReport.score_label }}</small>
        </div>
      </header>

      <section class="report-summary-grid" aria-label="本期简报摘要">
        <div class="report-summary-card">
          <span>记录时间</span>
          <strong>{{ displayReport.date_label }}</strong>
        </div>
        <div class="report-summary-card">
          <span>先聊这个</span>
          <strong>{{ displayReport.nextAction }}</strong>
        </div>
        <div class="report-summary-card">
          <span>过往记录</span>
          <strong>{{ displayReport.record_count }} 份</strong>
        </div>
      </section>

      <section class="report-visual-grid">
        <article class="report-panel report-panel--radar">
          <div class="report-panel__head">
            <span>关系五边形</span>
          </div>
          <div v-if="displayReport.dimensions.length" class="report-radar-layout">
            <svg class="report-radar" viewBox="0 0 440 390" role="img" :aria-label="radarAriaLabel">
              <polygon v-for="ring in radarRings" :key="ring.score" :points="ring.points" class="report-radar__grid" :class="{ 'report-radar__grid--outer': ring.score === 100 }" />
              <line v-for="axis in radarAxes" :key="`${axis.id}-axis`" :x1="RADAR_CENTER.x" :y1="RADAR_CENTER.y" :x2="axis.axisX" :y2="axis.axisY" class="report-radar__axis" />
              <polygon :points="radarValuePolygon" class="report-radar__shape" />
              <g v-for="axis in radarAxes" :key="axis.id">
                <circle :cx="axis.valueX" :cy="axis.valueY" r="4" class="report-radar__dot" />
                <text :x="axis.labelX" :y="axis.labelStartY" :text-anchor="axis.anchor" class="report-radar__label">
                  <tspan v-for="(line, index) in axis.labelLines" :key="index" :x="axis.labelX" :dy="index ? 20 : 0">{{ line }}</tspan>
                </text>
                <text :x="axis.valueLabelX" :y="axis.valueLabelY" :text-anchor="axis.anchor" class="report-radar__value">{{ axis.score }}</text>
              </g>
            </svg>
          </div>
          <p v-else class="report-panel__empty">暂无可核验的维度数据</p>
        </article>

        <article class="report-panel report-panel--trend">
          <div class="report-panel__head">
            <span>每日变化</span>
            <small>{{ isDemoMode ? '样例趋势' : '真实记录' }}</small>
          </div>
          <template v-if="trendChartPoints.length">
            <div class="report-trend-scroll" :tabindex="trendChartPoints.length > 7 ? 0 : undefined" role="region" aria-label="关系评分趋势图">
              <svg class="report-trend" :viewBox="`0 0 ${trendChart.width} 286`" :style="{ minWidth: trendChartPoints.length > 7 ? `${trendChart.width}px` : undefined }" role="img" :aria-label="trendAriaLabel">
                <g v-for="tick in trendChart.ticks" :key="tick.score">
                  <line :x1="trendChart.left" :y1="tick.y" :x2="trendChart.right" :y2="tick.y" class="report-trend__grid" />
                  <text :x="trendChart.left - 12" :y="tick.y + 5" text-anchor="end" class="report-trend__tick">{{ tick.score }}</text>
                </g>
                <polyline :points="trendPolyline" class="report-trend__line" />
                <g v-for="(point, index) in trendChartPoints" :key="`${point.label}-${index}`">
                  <title>{{ point.label }}，{{ point.score }}分</title>
                  <circle :cx="point.x" :cy="point.y" r="5" class="report-trend__dot" />
                  <text :x="point.x" :y="point.y - 15" text-anchor="middle" class="report-trend__score">{{ point.score }}</text>
                  <text :x="point.x" y="267" text-anchor="middle" class="report-trend__label">{{ point.shortLabel }}</text>
                </g>
              </svg>
            </div>
          </template>
          <p v-else class="report-panel__empty">还没有带评分的每日记录</p>
        </article>
      </section>

      <section class="report-copy-grid">
        <article class="report-copy-panel">
          <p class="eyebrow">洞察</p>
          <h3>值得留意的事</h3>
          <ul>
            <li v-for="item in displayReport.insights" :key="item">{{ item }}</li>
          </ul>
        </article>

        <article class="report-copy-panel report-copy-panel--accent">
          <p class="eyebrow">下一步</p>
          <h3>接下来先做这几件事</h3>
          <ul>
            <li v-for="item in displayReport.recommendations" :key="item">{{ item }}</li>
          </ul>
        </article>
      </section>
    </article>

    <div v-else class="report-empty">
      <img src="/favicon.svg" alt="亲健" />
      <strong>{{ loading ? '正在加载…' : generating ? '正在整理简报…' : '还没有简报' }}</strong>
      <p v-if="!loading && !generating && !notice">平时多记一两句生活日常，就能自动生成专属的暖心简报啦~</p>
    </div>

    <section v-if="displayHistory.length" class="report-history">
      <div class="report-history__head">
        <h3>查看往期{{ reportTypeLabel(reportStore.reportType) }}</h3>
      </div>
      <div class="history-timeline">
        <button v-for="item in displayHistory" :key="item.id" class="history-item" :class="{ 'history-item--selected': item.id === displayReport?.id }" :aria-pressed="item.id === displayReport?.id" type="button" @click="loadReport(item)">
          <strong>{{ reportPeriodLabel(item) }}</strong>
          <span v-if="item.id === displayReport?.id">正在查看</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { createLatestRequest } from '@/utils/taskSchedule'
import { createReportPoller } from '@/utils/reportPolling'
import { RADAR_CENTER, buildRadarAxes, radarPolygon, buildTrendChart, normalizeChartScore } from '@/utils/reportCharts'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useReportStore } from '@/stores/report'
import { useUserStore } from '@/stores/user'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { extractReportInsights, extractReportRecommendations } from '@/utils/reportContent'
import { buildSampleReports, reportPeriodLabel, selectReportHistory } from '@/utils/reportPeriods'

const router = useRouter()
const reportStore = useReportStore()
const userStore = useUserStore()

const report = ref(null)
const history = ref([])
const trend = ref([])
const selectedPairId = ref('')
const loading = ref(false)
const generating = ref(false)
const notice = ref('')
const loads = createLatestRequest()
const poller = createReportPoller()
let disposed = false
const scopeKey = () => JSON.stringify([userStore.token, userStore.me?.id, selectedPairId.value, reportStore.reportType])
const selectedHistoryItem = ref(null)

const isDemoMode = computed(() => userStore.isDemoMode)
const availableReportPairs = computed(() => {
  const pairs = isDemoMode.value ? (userStore.pairs?.length ? userStore.pairs : demoFixture.pairs) : (userStore.pairs || [])
  return pairs.filter((pair) => (
    isDemoMode.value
      ? pair?.status !== 'removed'
      : pair?.status === 'active'
  ))
})
const selectedPair = computed(() => availableReportPairs.value.find((pair) => pair.id === selectedPairId.value) || null)

const displayReport = computed(() => {
  if (isDemoMode.value) return buildDemoReport()
  if (!report.value || ['pending', 'failed'].includes(report.value.status)) return null

  const score = normalizeChartScore(report.value.health_score ?? report.value.content?.health_score)
  const fallbackSummary = report.value.summary || report.value.content?.insight || report.value.content?.suggestion || '暂无结论'
  const fallbackInsights = extractReportInsights(report.value)
  const fallbackRecommendations = extractReportRecommendations(report.value)
  const scopeName = partnerName(selectedPair.value) || userStore.partnerName || '当前关系'

  return {
    id: report.value.id,
    report_type: report.value.report_type || reportStore.reportType,
    date_label: reportPeriodLabel(report.value),
    relation_label: selectedPair.value ? `${pairTypeLabel(selectedPair.value)} · ${scopeName}` : '个人记录',
    scope_name: selectedPair.value ? scopeName : '个人记录',
    health_score: score ?? '—',
    score_label: score === null ? '暂无评分' : '关系评分',
    summary: fallbackSummary,
    nextAction: fallbackRecommendations[0] || '先保留一个小动作，再继续观察。',
    record_count: selectReportHistory(history.value, reportStore.reportType).length,
    tags: [],
    quick_links: ['关系日历', '发前先过一遍'],
    dimensions: extractReportDimensions(report.value),
    trend_points: normalizeTrendPoints(trend.value),
    insights: fallbackInsights,
    recommendations: fallbackRecommendations,
    history: history.value,
  }
})

const displayHistory = computed(() => {
  if (isDemoMode.value) return displayReport.value?.history || []
  return selectReportHistory(history.value, reportStore.reportType)
})

const radarAxes = computed(() => buildRadarAxes(displayReport.value?.dimensions || []))
const radarRings = computed(() => [25, 50, 75, 100].map(score => ({ score, points: radarPolygon(score, radarAxes.value.length) })))

const radarValuePolygon = computed(() => radarAxes.value.map((axis) => `${axis.valueX.toFixed(1)},${axis.valueY.toFixed(1)}`).join(' '))
const radarAriaLabel = computed(() =>
  `关系五边形，${(displayReport.value?.dimensions || []).map((axis) => `${axis.label}${axis.score}分`).join('，')}`
)

const trendChart = computed(() => buildTrendChart(displayReport.value?.trend_points || []))
const trendChartPoints = computed(() => trendChart.value.points)
const trendPolyline = computed(() => trendChartPoints.value.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' '))
const trendAriaLabel = computed(() =>
  `关系评分，纵轴 ${trendChart.value.min} 至 ${trendChart.value.max} 分。${trendChartPoints.value.map(point => `${point.label}${point.score}分`).join('，')}`
)

onMounted(async () => {
  selectedPairId.value = isDemoMode.value
    ? demoFixture.reportDashboard?.pair_id || userStore.currentPair?.id || ''
    : userStore.currentPair?.id || userStore.activePairId || ''
  if (!isDemoMode.value && !selectedPairId.value) reportStore.reportType = 'daily'
  await loadData()
})

function cancelPending() {
  loads.invalidate()
  poller.stop()
  loading.value = false
  generating.value = false
}

onBeforeUnmount(() => { disposed = true; cancelPending() })
watch(() => [userStore.token, userStore.me?.id], () => {
  cancelPending()
  report.value = null; history.value = []; trend.value = []
  selectedPairId.value = userStore.activePairId || ''
  reportStore.reset()
  if (userStore.isLoggedIn) loadData()
})

async function loadData() {
  cancelPending()
  const requestCurrent = loads.begin()
  const scope = scopeKey()
  const current = () => !disposed && requestCurrent() && scopeKey() === scope
  notice.value = ''
  report.value = null; history.value = []; trend.value = []
  if (isDemoMode.value) {
    report.value = cloneDemo(demoFixture.reportDashboard)
    history.value = cloneDemo(demoFixture.reportDashboard?.history || [])
    trend.value = cloneDemo(demoFixture.reportDashboard?.trend_points || [])
    return
  }
  const pairId = selectedPairId.value || null
  const type = reportStore.reportType
  loading.value = true
  const results = await Promise.allSettled([
    reportStore.loadLatest(pairId, type),
    reportStore.loadHistory(pairId, type),
    api.getReportTrend(pairId, 14),
  ])
  if (!current()) return
  loading.value = false
  report.value = results[0].status === 'fulfilled' ? results[0].value : null
  history.value = results[1].status === 'fulfilled' ? results[1].value : []
  trend.value = results[2].status === 'fulfilled' ? results[2].value?.trend || [] : []
  if (results[0].status === 'rejected') notice.value = results[0].reason?.message || '简报没加载出来，请重试'
  if (report.value?.status === 'failed') notice.value = '这次简报没生成成功，可以再试一次'
  if (report.value?.status === 'pending') startPolling(pairId, type, scope)
}

function startPolling(pairId, type, scope) {
  generating.value = true
  const current = () => !disposed && scopeKey() === scope
  poller.start({
    read: () => api.getLatestReport(pairId, type),
    onResult(result) {
      if (!current()) { poller.stop(); return }
      if (result?.status === 'completed') {
        generating.value = false
        loadData()
      } else if (result?.status === 'failed') {
        generating.value = false
        notice.value = '这次简报没生成成功，可以再试一次'
      }
    },
    onError(error) {
      if (!current()) return
      generating.value = false
      notice.value = error.message || '暂时查不到生成进度，稍后再刷新'
    },
    onTimeout() {
      if (!current()) return
      generating.value = false
      notice.value = '还在生成，稍后刷新查看'
    },
  })
}

async function switchType(type) {
  if ((!isDemoMode.value && !selectedPairId.value && type !== 'daily') || reportStore.reportType === type) return
  reportStore.reportType = type
  selectedHistoryItem.value = null
  await loadData()
}

async function generateReport() {
  if (generating.value || loading.value) return
  if (isDemoMode.value) {
    selectedHistoryItem.value = null
    await loadData()
    return
  }
  const pairId = selectedPairId.value || null
  const type = reportStore.reportType
  const scope = scopeKey()
  const current = () => !disposed && scopeKey() === scope
  generating.value = true
  notice.value = ''
  try {
    await reportStore.generate(pairId, type)
    if (current()) await loadData()
  } catch (error) {
    if (current()) { generating.value = false; notice.value = error.message || '这次没生成成功，请重试' }
  }
}

async function changeReportPair() {
  if (!isDemoMode.value && !selectedPairId.value) reportStore.reportType = 'daily'
  selectedHistoryItem.value = null
  await loadData()
}

function loadReport(item) {
  cancelPending()
  notice.value = ''
  if (isDemoMode.value) {
    selectedHistoryItem.value = item
    return
  }
  report.value = item
}

function openQuickLink(label) {
  if (label === '关系日历') {
    router.push('/timeline')
    return
  }
  if (label === '发前先过一遍') {
    router.push('/message-simulation')
  }
}

function buildDemoReport() {
  const base = cloneDemo(demoFixture.reportDashboard)
  const selectedPair = availableReportPairs.value.find((pair) => pair.id === selectedPairId.value)
  const metrics = demoFixture.relationshipMetrics?.[selectedPairId.value] || {}
  const isBasePair = !selectedPairId.value || selectedPairId.value === base.pair_id
  const selectedScore = Number(metrics.score || base.health_score)
  const selectedName = partnerName(selectedPair) || base.scope_name
  const selectedHistory = selectedHistoryItem.value

  if (!isBasePair) {
    base.pair_id = selectedPairId.value
    base.scope_name = selectedName
    base.relation_label = `${pairTypeLabel(selectedPair)} · ${selectedName}`
    base.health_score = selectedScore
    base.summary = metrics.summary || base.summary
    base.nextAction = metrics.nextAction || base.nextAction
    base.dimensions = buildFallbackDimensions(selectedScore)
  }

  const rows = buildSampleReports(base, reportStore.reportType)
  const current = rows.find(row => row.id === selectedHistory?.id) || rows[0]
  return { ...current, date_label: reportPeriodLabel(current), history: rows, record_count: rows.length, trend_points: normalizeTrendPoints(current.trend_points) }
}

function buildFallbackDimensions(score) {
  const base = Number(score || 72)
  return [
    { id: 'expression', label: '表达', score: clamp(base + 4, 0, 100) },
    { id: 'trust', label: '信任', score: clamp(base - 2, 0, 100) },
    { id: 'repair', label: '缓和', score: clamp(base + 1, 0, 100) },
    { id: 'future', label: '愿景', score: clamp(base - 8, 0, 100) },
    { id: 'vitality', label: '活力', score: clamp(base + 6, 0, 100) },
  ]
}



function extractReportDimensions(value) {
  const raw = value?.dimensions || value?.content?.dimensions || value?.content?.dimension_scores
  if (Array.isArray(raw)) {
    return raw
      .map((item, index) => ({
        id: String(item?.id || item?.key || `dimension-${index}`),
        label: String(item?.label || item?.name || '').trim(),
        score: clampScore(item?.score ?? item?.value),
      }))
      .filter((item) => item.label)
      .slice(0, 8)
  }
  if (raw && typeof raw === 'object') {
    return Object.entries(raw)
      .map(([key, score]) => ({ id: key, label: key, score: clampScore(score) }))
      .slice(0, 8)
  }
  return []
}

function normalizeTrendPoints(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => ({
      label: formatShortDate(item?.date || item?.label),
      score: normalizeChartScore(item?.score),
    }))
    .filter((item) => item.label && item.score !== null)
}

function reportTypeLabel(type) {
  return type === 'weekly' ? '周报' : type === 'monthly' ? '月报' : '日报'
}

function pairTypeLabel(pair) {
  const typeMap = { couple: '情侣', romantic: '情侣', friend: '朋友', family: '家人', custom: '关系' }
  return typeMap[pair?.type] || pair?.type_label || '关系'
}

function partnerName(pair) {
  return pair?.custom_partner_nickname || pair?.partner_nickname || pair?.partner_email || pair?.partner_phone || ''
}

function formatShortDate(v) {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function clampScore(value) {
  return clamp(Number(value || 0), 0, 100)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}
</script>

<style scoped>
.report-page {
  width: min(1200px, calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 36px;
}

.history-item--selected { outline: 2px solid #528570; background: #edf7f1; }
.report-tabs button:disabled { opacity: .45; cursor: not-allowed; }
.report-personal-note { color: var(--ink-soft); margin: 0; font-size: 13px; }
select.report-scope-selector__button { max-width: 100%; color: #305d68; font: inherit; cursor: pointer; }

.report-hero {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 20px;
  padding: 42px 0 28px;
}

.report-hero__copy {
  grid-column: 2;
  text-align: center;
}

.report-hero h2 {
  max-width: 470px;
  margin: 0 auto;
  font-family: var(--font-serif);
  font-size: clamp(28px, 3vw, 36px);
  line-height: 1.18;
}

.report-refresh {
  grid-column: 3;
  justify-self: start;
  min-width: 180px;
}

.report-scope-card,
.report-paper,
.report-history,
.report-empty {
  border: 1px solid rgba(211, 194, 176, 0.72);
  border-radius: 28px;
  background: rgba(255, 253, 249, 0.76);
  box-shadow: 0 22px 54px rgba(103, 76, 55, 0.08);
}

.report-scope-card {
  display: grid;
  gap: 18px;
  padding: 20px;
  margin-bottom: 18px;
}

.report-tabs {
  width: min(430px, 100%);
  margin: 0 auto;
}

.report-scope-selector {
  display: grid;
  gap: 8px;
}

.report-scope-selector > label {
  color: var(--ink-faint);
  font-size: 13px;
}

.report-scope-selector__button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 54px;
  padding: 0 18px;
  border: 1px solid rgba(218, 203, 187, 0.76);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.68);
  color: var(--ink-blue);
  text-align: left;
}

.report-scope-selector__button strong {
  font-size: 18px;
}

.report-scope-selector__button em {
  color: var(--ink-blue);
  font-size: 14px;
  font-style: normal;
}

.report-paper {
  padding: 22px;
}

.report-paper__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 24px;
  align-items: start;
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 18px;
  color: var(--ink-faint);
  font-size: 13px;
  font-weight: 700;
}

.report-meta span {
  padding: 6px 10px;
  border: 1px solid rgba(218, 203, 187, 0.62);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
}

.report-paper__intro h3 {
  max-width: 800px;
  color: var(--ink-blue);
  font-family: var(--font-serif);
  font-size: clamp(30px, 3.5vw, 44px);
  line-height: 1.25;
}

.report-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 20px;
}

.report-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(215, 104, 72, 0.22);
  border-radius: 9px;
  color: var(--seal-deep);
  background: rgba(250, 227, 219, 0.7);
  font-size: 13px;
  font-weight: 800;
}

.report-chip:first-child {
  border-color: rgba(77, 122, 85, 0.24);
  color: var(--success);
  background: var(--success-soft);
}

.report-chip--action {
  border-color: rgba(210, 190, 168, 0.68);
  color: var(--ink-blue);
  background: rgba(255, 255, 255, 0.66);
}

.report-score {
  display: grid;
  place-items: center;
  min-height: 182px;
  border: 1px solid rgba(142, 186, 207, 0.42);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(235, 247, 250, 0.94), rgba(255, 253, 249, 0.88));
  color: var(--ink-blue);
  text-align: center;
}

.report-score span {
  font-family: var(--font-serif);
  font-size: 52px;
  line-height: 1;
}

.report-score small {
  color: rgba(96, 132, 137, 0.54);
  font-size: 12px;
  font-weight: 800;
}

.report-summary-grid {
  display: grid;
  grid-template-columns: 1fr 1.35fr 1fr;
  gap: 12px;
  margin-top: 22px;
}

.report-summary-card {
  min-height: 92px;
  padding: 18px;
  border: 1px solid rgba(218, 203, 187, 0.64);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.56);
}

.report-summary-card span,
.report-panel__head span {
  display: block;
  color: var(--ink-faint);
  font-size: 13px;
  font-weight: 700;
}

.report-summary-card strong {
  display: block;
  margin-top: 12px;
  color: var(--ink-blue);
  font-size: 17px;
  line-height: 1.55;
}

.report-visual-grid,
.report-copy-grid {
  display: grid;
  grid-template-columns: 1fr 1.08fr;
  gap: 16px;
  margin-top: 16px;
}

.report-panel,
.report-copy-panel {
  border: 1px solid rgba(218, 203, 187, 0.66);
  border-radius: 24px;
  background:
    radial-gradient(circle at 92% 8%, rgba(220, 235, 238, 0.36), transparent 34%),
    rgba(255, 255, 255, 0.58);
}

.report-panel {
  min-height: 320px;
  padding: 20px;
}

.report-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.report-panel__head strong {
  color: var(--ink-blue);
  font-family: var(--font-serif);
  font-size: 26px;
}

.report-panel__empty {
  display: grid;
  min-height: 230px;
  margin: 16px 0 0;
  place-items: center;
  color: var(--ink-faint);
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}

.report-radar-layout {
  display: grid;
  place-items: center;
  margin-top: 12px;
}

.report-radar {
  display: block;
  width: min(440px, 100%);
  height: auto;
}

.report-radar__grid {
  fill: none;
  stroke: rgba(183, 138, 116, 0.25);
  stroke-width: 1;
}

.report-radar__grid--outer {
  stroke: rgba(156, 111, 89, 0.48);
  stroke-width: 1.5;
}

.report-radar__axis { stroke: rgba(183, 138, 116, 0.22); }

.report-radar__shape {
  fill: rgba(215, 104, 72, 0.15);
  stroke: var(--seal);
  stroke-width: 2.5;
  stroke-linejoin: round;
}

.report-radar__dot { fill: var(--seal); stroke: #fffaf4; stroke-width: 2; }

.report-radar__label { fill: var(--ink-blue); font-size: 19px; font-weight: 650; }
.report-radar__value { fill: var(--seal-deep); font-size: 29px; font-weight: 750; font-variant-numeric: tabular-nums; }

.report-panel__head small { color: var(--ink-faint); font-size: 13px; font-weight: 500; }
.report-panel--trend { display: flex; flex-direction: column; min-width: 0; }

.report-trend-legend {
  display: flex;
  gap: 9px;
  align-items: center;
  margin-top: 22px;
  color: var(--ink-soft);
  font-size: 14px;
}

.report-trend-legend i { width: 24px; height: 3px; border-radius: 3px; background: var(--seal); }
.report-trend-legend small { margin-left: auto; color: var(--ink-faint); font-size: 12px; }
.report-trend-scroll { width: 100%; min-width: 0; overflow-x: auto; margin: auto 0; scrollbar-width: thin; }
.report-trend-scroll:focus-visible { outline: 2px solid var(--seal); outline-offset: 3px; }

.report-trend { display: block; width: 100%; height: auto; }
.report-trend__grid { stroke: rgba(169, 153, 135, 0.35); stroke-dasharray: 4 6; }
.report-trend__line { fill: none; stroke: var(--seal); stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.report-trend__dot { fill: var(--seal); stroke: #fffaf4; stroke-width: 2.5; }
.report-trend__score { fill: var(--seal-deep); font-size: 19px; font-weight: 750; paint-order: stroke; stroke: #fffaf4; stroke-width: 4; stroke-linejoin: round; font-variant-numeric: tabular-nums; }
.report-trend__label { fill: var(--ink-soft); font-size: 16px; }
.report-trend__tick { fill: var(--ink-faint); font-size: 15px; font-variant-numeric: tabular-nums; }
.report-trend-footer { display: flex; flex-wrap: wrap; gap: 8px 16px; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 1px solid rgba(218, 203, 187, 0.5); }
.report-trend-footer small { color: var(--ink-faint); font-size: 12px; }
.report-trend-footer strong { color: var(--ink-blue); font-size: 14px; font-weight: 600; }

.report-copy-panel {
  padding: 24px;
}

.report-copy-panel--accent {
  border-color: rgba(215, 104, 72, 0.24);
  background:
    radial-gradient(circle at 92% 8%, rgba(250, 227, 219, 0.44), transparent 32%),
    rgba(255, 250, 247, 0.7);
}

.report-copy-panel h3 {
  margin-top: 8px;
  color: var(--ink-blue);
  font-family: var(--font-serif);
  font-size: 25px;
}

.report-copy-panel ul {
  display: grid;
  gap: 12px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
  color: var(--ink-soft);
  font-size: 15px;
  line-height: 1.75;
}

.report-copy-panel li {
  position: relative;
  padding-left: 18px;
}

.report-copy-panel li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.78em;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--ink-blue);
}

.report-copy-panel--accent li::before {
  background: var(--seal);
}

.report-empty {
  display: grid;
  place-items: center;
  min-height: 260px;
  padding: 36px 20px;
  color: var(--ink-soft);
  text-align: center;
}

.report-empty img {
  width: 44px;
  height: 44px;
  margin-bottom: 12px;
  border-radius: var(--radius-lg);
}

.report-empty strong {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 18px;
}

.report-history {
  margin-top: 18px;
  padding: 24px;
}

.report-history__head h3 {
  margin-top: 8px;
  color: var(--ink-blue);
  font-family: var(--font-serif);
  font-size: 27px;
}

.history-timeline {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.history-item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-height: 48px;
  padding: 0 16px;
  border: 1px solid rgba(143, 184, 198, 0.34);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: var(--ink-blue);
  text-align: left;
}

.history-item strong {
  font-size: 15px;
}

.history-item span,
.history-item small {
  color: var(--ink-faint);
  font-size: 14px;
  font-weight: 800;
}

@media (max-width: 900px) {
  .report-hero,
  .report-paper__head,
  .report-summary-grid,
  .report-visual-grid,
  .report-copy-grid {
    grid-template-columns: 1fr;
  }

  .report-hero__copy,
  .report-refresh {
    grid-column: auto;
  }

  .report-refresh {
    justify-self: stretch;
  }

  .report-paper__intro h3 {
    font-size: 30px;
  }

  .report-score {
    min-height: 118px;
  }
}

@media (max-width: 767px) {
  .report-page {
    width: min(100% - 16px, 560px);
    padding-bottom: 86px;
  }

  .report-hero {
    gap: 16px;
    padding: 12px 36px 14px;
  }

  .report-hero h2 {
    font-size: 22px;
  }

  .report-refresh {
    min-width: 0;
    min-height: 42px;
  }

  .report-scope-card,
  .report-paper,
  .report-history,
  .report-empty {
    border-radius: 18px;
  }

  .report-scope-card {
    padding: 14px;
  }

  .report-paper {
    padding: 12px;
  }

  .report-paper__head {
    gap: 16px;
  }

  .report-meta {
    gap: 8px;
    margin-bottom: 12px;
  }

  .report-meta span {
    padding: 5px 8px;
    font-size: 12px;
  }

  .report-paper__intro h3 {
    font-size: 26px;
  }

  .report-score {
    min-height: 92px;
  }

  .report-score span {
    font-size: 40px;
  }

  .report-summary-card,
  .report-panel,
  .report-copy-panel {
    border-radius: 18px;
  }

  .report-summary-card {
    min-height: 78px;
    padding: 14px;
  }

  .report-panel { padding: 16px 12px; min-width: 0; }
  .report-trend-legend { margin-top: 18px; }
  .report-trend-scroll { margin: 10px 0; }
  .report-radar__label { font-size: 20px; }

  .report-copy-panel {
    padding: 18px;
  }

  .report-copy-panel h3 {
    font-size: 23px;
  }

  .report-history {
    padding: 18px 12px;
  }

  .history-item {
    grid-template-columns: 1fr auto auto;
    min-height: 44px;
    padding: 0 12px;
  }
}
</style>

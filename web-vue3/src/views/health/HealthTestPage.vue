<template>
  <div class="health-page page-shell page-shell--wide page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">体检</p>
        <h2>关系体检</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>

    <section class="card health-scope-card">
      <div class="health-scope-copy">
        <p class="eyebrow">先选入口</p>
        <h3>这次看哪条线</h3>
      </div>

      <div class="health-scope-grid">
        <button
          class="health-scope-option"
          :class="{ active: isSoloScope }"
          type="button"
          @click="selectScope(SOLO_SCOPE_ID)"
        >
          <span>先看自己</span>
          <strong>自我回看</strong>
        </button>

        <button
          v-for="pair in availablePairs"
          :key="pair.id"
          class="health-scope-option"
          :class="{ active: selectedScopeId === pair.id }"
          type="button"
          @click="selectScope(pair.id)"
        >
          <span>{{ pairTypeLabel(pair) }}</span>
          <strong>{{ pairPartnerName(pair) }}</strong>
        </button>
      </div>

      <div class="hero-actions">
        <span class="health-scope-current">当前将查看：{{ selectedScopeSummary }}</span>
        <button class="btn btn-primary" type="button" @click="confirmSelectedScope">
          {{ scopeActionLabel }}
        </button>
      </div>
    </section>

    <div v-if="!scopeConfirmed" class="card">
      <div class="empty-state">先确认这次要看的对象，再开始答题。</div>
    </div>

    <div v-else-if="loading" class="card">
      <div class="empty-state">正在加载这次体检题目…</div>
    </div>

    <template v-else>
      <div class="health-layout">
        <section class="card card-accent">
          <div class="card-header">
            <div>
              <p class="eyebrow">这次体检</p>
              <h3>{{ pack.title || defaultPackTitle }}</h3>
              <p class="health-scope-current health-scope-current--inline">{{ selectedScopeSummary }}</p>
            </div>
            <button class="btn btn-ghost btn-sm" :disabled="loading" @click="reloadPack">换一组题</button>
          </div>
          <div v-if="!showResultPanel && currentItem" class="health-question-wrap">
            <div class="progress-track">
              <span class="progress-track__fill" :style="{ width: `${progressPercent}%` }"></span>
            </div>
            <div class="health-progress-meta">
              <span>问题 {{ currentIndex + 1 }}/{{ questions.length }}</span>
              <span>{{ currentItem.dimension_label }}</span>
            </div>
            <h3 class="health-question">{{ currentItem.prompt }}</h3>
            <div class="stack-list">
              <button
                v-for="option in currentItem.options"
                :key="option.id"
                class="stack-item"
                :class="{ active: selectedOptionId(currentItem.item_id) === option.id }"
                type="button"
                @click="selectAnswer(currentItem, option)"
              >
                <div class="stack-item__content">
                  <strong>{{ option.label }}</strong>
                  <div class="stack-item__meta">{{ option.score }} 分</div>
                </div>
              </button>
            </div>
            <div class="health-question-actions" :class="{ 'health-question-actions--single': currentIndex === 0 }">
              <button v-if="currentIndex > 0" class="btn btn-ghost health-question-actions__button" @click="currentIndex--">上一步</button>
              <button
                v-if="currentIndex < questions.length - 1"
                class="btn btn-primary health-question-actions__button"
                :disabled="!selectedOptionId(currentItem.item_id)"
                @click="currentIndex++"
              >
                继续
              </button>
              <button
                v-else
                class="btn btn-primary health-question-actions__button"
                :disabled="!canSubmit"
                @click="submitAssessment"
              >
                {{ submitting ? '提交中…' : '查看结果' }}
              </button>
            </div>
          </div>

          <div v-else-if="result" class="health-result">
            <div class="health-result-hero">
              <div
                class="result-ring"
                :style="resultScoreStyle"
                role="img"
                :aria-label="`体检总分 ${result.total_score} 分，满分 100`"
              >
                <em>综合分</em>
                <span>{{ result.total_score }}</span>
                <b>/100</b>
              </div>
              <div class="health-result-copy">
                <p class="eyebrow">体检结果</p>
                <h3 class="health-result-title">{{ scoreTitle }}</h3>
              </div>
            </div>
            <div class="health-result-visuals">
              <article class="health-visual-card health-visual-card--radar">
                <div class="health-visual-card__head">
                  <span>关系五边形</span>
                  <strong>{{ healthRadarAverage }}</strong>
                </div>
                <div class="health-radar-layout">
                  <svg class="health-radar" viewBox="-24 0 288 230" role="img" :aria-label="healthRadarAriaLabel">
                    <polygon points="110,24 192,84 161,180 59,180 28,84" class="health-radar__grid" />
                    <polygon points="110,58 160,95 141,154 79,154 60,95" class="health-radar__grid health-radar__grid--inner" />
                    <text x="116" y="35" class="health-radar__scale">100</text>
                    <text x="116" y="64" class="health-radar__scale">70</text>
                    <line
                      v-for="axis in healthRadarAxes"
                      :key="`${axis.label}-axis`"
                      x1="110"
                      y1="110"
                      :x2="axis.x"
                      :y2="axis.y"
                      class="health-radar__axis"
                    />
                    <polygon :points="healthRadarPolygon" class="health-radar__shape" />
                    <g v-for="axis in healthRadarAxes" :key="axis.label">
                      <circle :cx="axis.valueX" :cy="axis.valueY" r="4" class="health-radar__dot" />
                      <text
                        :x="axis.valueLabelX"
                        :y="axis.valueLabelY"
                        :text-anchor="axis.valueTextAnchor"
                        class="health-radar__value"
                      >{{ axis.value }}</text>
                      <text
                        :x="axis.labelX"
                        :y="axis.labelY"
                        :text-anchor="axis.labelAnchor"
                        class="health-radar__label"
                      >{{ axis.shortLabel }}</text>
                    </g>
                  </svg>
                  <div class="health-radar-list">
                    <span v-for="axis in healthRadarAxes" :key="`${axis.label}-list`">
                      {{ axis.label }} <strong>{{ axis.value }}</strong>
                    </span>
                  </div>
                </div>
              </article>

              <article class="health-visual-card health-visual-card--trend">
                <div class="health-visual-card__head">
                  <span>最近变化</span>
                  <strong>{{ healthTrendSummary }}</strong>
                </div>
                <svg class="health-line-chart" viewBox="0 0 320 150" role="img" aria-label="最近体检变化折线图">
                  <path d="M24 118 H296 M24 82 H296 M24 46 H296" class="health-line-chart__grid" />
                  <polyline :points="healthTrendPolyline" class="health-line-chart__path" />
                  <circle
                    v-for="point in healthTrendChartPoints"
                    :key="point.label"
                    :cx="point.x"
                    :cy="point.y"
                    r="4"
                    class="health-line-chart__dot"
                  />
                  <text
                    v-for="point in healthTrendChartPoints"
                    :key="`${point.label}-score`"
                    :x="point.x"
                    :y="point.labelY"
                    text-anchor="middle"
                    class="health-line-chart__value"
                  >{{ point.score }}</text>
                </svg>
                <div class="health-line-chart__axis">
                  <span v-for="point in healthTrendChartPoints" :key="`${point.label}-axis`">{{ point.label }}</span>
                </div>
              </article>
            </div>
            <div class="health-dimension-grid">
              <article
                v-for="dimension in result.dimension_scores"
                :key="dimension.id"
                class="health-dimension-card"
              >
                <span>{{ dimension.label }}</span>
                <strong>{{ dimension.score ?? '--' }}</strong>
                <div class="health-dimension-meter" aria-hidden="true">
                  <i :style="{ width: dimensionScoreWidth(dimension) }"></i>
                </div>
              </article>
            </div>
            <div class="health-suggestions">
              <p class="eyebrow">这次先照顾</p>
              <ul class="plain-list">
                <li v-for="item in briefSuggestions" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="hero-actions health-result-actions">
              <button class="btn btn-secondary" :disabled="loading" @click="restartAssessment">重新测试</button>
            </div>
          </div>
        </section>

        <aside class="health-side">
          <section class="card">
            <div class="card-header">
              <div>
                <p class="eyebrow">最近一次</p>
                <h3>{{ latest?.total_score ?? pack.latest_score ?? '--' }}</h3>
              </div>
            </div>
          </section>

          <section class="card">
            <div class="card-header">
              <div>
                <p class="eyebrow">趋势</p>
                <h3>最近 {{ trendPoints.length || 0 }} 次</h3>
              </div>
            </div>
            <div v-if="trendPoints.length" class="health-trend-list">
              <article
                v-for="point in trendPoints"
                :key="point.event_id"
                class="health-trend-item"
              >
                <span>{{ formatDate(point.submitted_at) }}</span>
                <strong>{{ point.total_score }}</strong>
              </article>
            </div>
            <div v-else class="empty-state">暂无趋势。</div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'

import { api } from '@/api'
import { buildDemoAssessmentPack, cloneDemo, demoFixture } from '@/demo/fixtures'
import { useUserStore } from '@/stores/user'
import { relationshipTypeLabel } from '@/utils/displayText'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'

const SOLO_SCOPE_ID = 'solo-self-check'

const userStore = useUserStore()
const showToast = inject('showToast', () => {})

const loading = ref(false)
const submitting = ref(false)
const pack = ref({ items: [] })
const latest = ref(null)
const trend = ref({ trend_points: [] })
const answers = ref({})
const currentIndex = ref(0)
const submitted = ref(false)
const selectedScopeId = ref(SOLO_SCOPE_ID)
const scopeConfirmed = ref(false)
const assessmentPackGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })
const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)

const availablePairs = computed(() => (userStore.pairs || []).filter((pair) => pair.status === 'active'))
const selectedPair = computed(() =>
  availablePairs.value.find((pair) => pair.id === selectedScopeId.value) || null
)
const isSoloScope = computed(() => selectedScopeId.value === SOLO_SCOPE_ID)
const defaultPackTitle = computed(() => (isSoloScope.value ? '自我回看' : '关系体检'))
const selectedScopeSummary = computed(() => {
  if (isSoloScope.value) return '自我回看'
  if (!selectedPair.value) return '这段关系'
  return `${pairTypeLabel(selectedPair.value)} · ${pairPartnerName(selectedPair.value)}`
})
const scopeActionLabel = computed(() => {
  if (experienceMode.value.isDemoMode) {
    return isSoloScope.value ? '查看自我回看样例' : '查看关系体检样例'
  }
  return isSoloScope.value ? '开始自我回看' : '开始这段关系的体检'
})
const questions = computed(() => pack.value.items || [])
const currentItem = computed(() => questions.value[currentIndex.value] || null)
const progressPercent = computed(() =>
  questions.value.length ? Math.round(((currentIndex.value + 1) / questions.value.length) * 100) : 0
)
const canSubmit = computed(() =>
  questions.value.length > 0 && questions.value.every((item) => Boolean(selectedOptionId(item.item_id)))
)
const result = computed(() => latest.value)
const trendPoints = computed(() => trend.value?.trend_points || [])
const showResultPanel = computed(() => Boolean(result.value) && submitted.value)
const assessmentMethodNote = computed(() => {
  if (experienceMode.value.isDemoMode) {
    return '样例题目，不写入真实测评。'
  }
  return '阶段回看，不代替专业诊断。'
})
const interpretationNote = computed(() =>
  isSoloScope.value
    ? '一次自我回看。'
    : '一次关系回看。'
)
const scoreTitle = computed(() => {
  const score = Number(result.value?.total_score || 0)
  if (score >= 80) return '状态挺稳'
  if (score >= 65) return '还算顺'
  if (score >= 50) return '有些地方要照顾'
  return '先慢一点'
})
const resultScoreStyle = computed(() => {
  const score = Math.min(100, Math.max(0, Number(result.value?.total_score || 0)))
  return {
    '--result-score-deg': `${score * 3.6}deg`,
  }
})
const briefSuggestions = computed(() => {
  const dimensionScores = [...(result.value?.dimension_scores || [])]
    .filter((item) => item.score !== null && item.score !== undefined)
    .sort((a, b) => Number(a.score) - Number(b.score))
    .slice(0, 2)

  if (!dimensionScores.length) {
    return [isSoloScope.value
      ? '先完成这次自我回看。'
      : '先完成这次体检。']
  }

  return dimensionScores.map((item) => suggestionForDimension(item.id))
})

function dimensionScoreWidth(dimension) {
  const score = Math.min(100, Math.max(0, Number(dimension?.score || 0)))
  return `${score}%`
}

const healthRadarAxes = computed(() => {
  const center = { x: 110, y: 110 }
  const outer = [
    { x: 110, y: 24, angle: -90 },
    { x: 192, y: 84, angle: -18 },
    { x: 161, y: 180, angle: 54 },
    { x: 59, y: 180, angle: 126 },
    { x: 28, y: 84, angle: 198 },
  ]
  const dimensions = (result.value?.dimension_scores || []).slice(0, 5)
  return outer.map((point, index) => {
    const dimension = dimensions[index] || { label: `维度${index + 1}`, score: 0 }
    const value = Math.min(100, Math.max(0, Number(dimension.score || 0)))
    const ratio = value / 100
    const valueX = center.x + (point.x - center.x) * ratio
    const valueY = center.y + (point.y - center.y) * ratio
    const labelPosition = radarLabelPosition(point.angle, 18)
    const valuePosition = radarLabelPosition(point.angle, -10)
    return {
      ...point,
      label: dimension.label,
      shortLabel: shortDimensionLabel(dimension),
      value,
      valueX,
      valueY,
      labelX: point.x + labelPosition.x,
      labelY: point.y + labelPosition.y,
      labelAnchor: point.x > center.x ? 'end' : (point.x < center.x ? 'start' : 'middle'),
      valueLabelX: valueX + valuePosition.x,
      valueLabelY: valueY + valuePosition.y,
      valueTextAnchor: valueX > center.x ? 'end' : 'start',
    }
  })
})

const healthRadarPolygon = computed(() => healthRadarAxes.value.map((axis) => `${axis.valueX},${axis.valueY}`).join(' '))

const healthRadarAverage = computed(() => {
  const axes = healthRadarAxes.value
  if (!axes.length) return 0
  return Math.round(axes.reduce((sum, axis) => sum + Number(axis.value || 0), 0) / axes.length)
})

const healthRadarLowest = computed(() =>
  healthRadarAxes.value.reduce((lowest, axis) => (axis.value < lowest.value ? axis : lowest), healthRadarAxes.value[0] || { label: '--', value: '--' })
)

const healthRadarAriaLabel = computed(() =>
  `关系五边形，${healthRadarAxes.value.map((axis) => `${axis.label}${axis.value}分`).join('，')}`
)

const healthTrendChartPoints = computed(() => {
  const points = trendPoints.value.slice(-6)
  if (!points.length) {
    const score = Number(result.value?.total_score || 0)
    const y = scoreToTrendY(score)
    return [{ label: '本次', x: 160, y, labelY: Math.max(16, y - 10), score }]
  }
  const maxIndex = Math.max(points.length - 1, 1)
  return points.map((point, index) => {
    const score = Number(point.total_score || 0)
    return {
      label: formatDate(point.submitted_at) || `第${index + 1}次`,
      score,
      x: 24 + (272 * index) / maxIndex,
      y: scoreToTrendY(score),
      labelY: Math.max(16, scoreToTrendY(score) - 10),
    }
  })
})

const healthTrendPolyline = computed(() => healthTrendChartPoints.value.map((point) => `${point.x},${point.y}`).join(' '))

const healthTrendSummary = computed(() => {
  const points = healthTrendChartPoints.value
  if (points.length < 2) return `${result.value?.total_score ?? '--'}分`
  const diff = Number(points[points.length - 1].score || 0) - Number(points[points.length - 2].score || 0)
  if (diff > 0) return `+${diff}`
  return `${diff}`
})

const healthTrendNote = computed(() => {
  const lowest = healthRadarLowest.value
  if (!lowest?.label || lowest.label === '--') return '这条线会随着每次体检更新。'
  return `先看最低项「${lowest.label}」，再决定今天补哪一步。`
})

function radarLabelPosition(angle, distance) {
  const radians = (angle * Math.PI) / 180
  return {
    x: Math.cos(radians) * distance,
    y: Math.sin(radians) * distance,
  }
}

function shortDimensionLabel(dimension) {
  const id = String(dimension?.id || '')
  const label = String(dimension?.label || '')
  const map = {
    connection: '表达',
    trust: '信任',
  repair: '缓和',
    shared_future: '愿景',
    vitality: '活力',
  }
  return map[id] || label.replace(/^关系/, '').slice(0, 4) || '维度'
}

function scoreToTrendY(scoreValue) {
  const score = Math.min(100, Math.max(0, Number(scoreValue || 0)))
  return 124 - score * 0.88
}

watch(
  () => [userStore.activePairId, availablePairs.value.map((pair) => pair.id).join(',')],
  () => {
    if (scopeConfirmed.value) return
    const currentPairId = userStore.activePairId
    if (availablePairs.value.some((pair) => pair.id === currentPairId)) {
      selectedScopeId.value = currentPairId
      return
    }
    if (!availablePairs.value.some((pair) => pair.id === selectedScopeId.value)) {
      selectedScopeId.value = SOLO_SCOPE_ID
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (availablePairs.value.some((pair) => pair.id === userStore.activePairId)) {
    selectedScopeId.value = userStore.activePairId
  }
})

function currentPairId() {
  return isSoloScope.value ? null : selectedPair.value?.id || null
}

function pairTypeLabel(pair) {
  if (!pair) return '关系'
  if (pair.is_long_distance && ['couple', 'spouse'].includes(pair.type)) return '异地关系'
  return relationshipTypeLabel(pair.type)
}

function pairPartnerName(pair) {
  if (!pair) return '对方'
  return pair.custom_partner_nickname
    || pair.partner_nickname
    || pair.partner_email
    || pair.partner_phone
    || '对方'
}

function selectScope(scopeId) {
  if (selectedScopeId.value === scopeId && !scopeConfirmed.value) return
  selectedScopeId.value = scopeId
  scopeConfirmed.value = false
}

async function confirmSelectedScope() {
  if (!isSoloScope.value && !selectedPair.value) {
    showToast('先选一段关系，再开始体检')
    return
  }

  if (!isSoloScope.value && selectedPair.value) {
    await userStore.switchPair(selectedPair.value.id)
  }
  scopeConfirmed.value = true
  await loadAssessment()
}

function selectedOptionId(itemId) {
  return answers.value[itemId]?.option_id || ''
}

function selectAnswer(item, option) {
  answers.value = {
    ...answers.value,
    [item.item_id]: {
      item_id: item.item_id,
      dim: item.dimension,
      score: option.score,
      option_id: option.id,
    },
  }
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function suggestionForDimension(dimensionId) {
  const soloMap = {
    connection: '先把“连接与表达”放轻一点，下一次只把你真正介意的一点说清楚就够了。',
    trust: '先照顾“信任与安全”，少做猜测，多看一眼什么会让你真的安心。',
    repair: '先补“缓和能力”，情绪起来时先停一下，只处理一个点。',
    shared_future: '先稳住“共同愿景”，写一句你接下来最想保住的关系状态。',
    vitality: '先照顾“关系活力”，给自己留一个低压力、能完成的小靠近动作。',
  }
  const pairMap = {
    connection: '先把“连接与表达”放轻一点，今天只做一次 10 分钟连线就够了。',
    trust: '先照顾“信任与安全”，少做猜测，多做一次明确回应。',
    repair: '先补“缓和能力”，摩擦起来时先慢下来，再只处理一个点。',
    shared_future: '先稳住“共同愿景”，补一句对接下来还想一起保留什么。',
    vitality: '先照顾“关系活力”，安排一个低压力、能完成的小陪伴动作。',
  }
  const map = isSoloScope.value ? soloMap : pairMap
  return map[String(dimensionId || '')] || '先从最轻的一步开始，把关系节奏接回来。'
}

async function loadAssessment() {
  loading.value = true
  submitted.value = false
  currentIndex.value = 0
  answers.value = {}
  try {
    if (experienceMode.value.isDemoMode) {
      pack.value = buildDemoAssessmentPack(isSoloScope.value ? 'solo' : selectedPair.value)
      latest.value = {
        ...cloneDemo(demoFixture.assessmentLatest),
        scope: isSoloScope.value ? 'solo' : 'pair',
        change_summary: isSoloScope.value
          ? '这更像一次自我整理，先从最低的一两维开始，不用急着一次改很多。'
          : cloneDemo(demoFixture.assessmentLatest).change_summary,
      }
      trend.value = {
        ...cloneDemo(demoFixture.assessmentTrend),
        trend_points: cloneDemo(demoFixture.assessmentTrend.trend_points).map((point) => ({
          ...point,
          scope: isSoloScope.value ? 'solo' : point.scope,
        })),
      }
      return
    }

    const pairId = currentPairId()
    const [packRes, latestRes, trendRes] = await Promise.allSettled([
      api.getWeeklyAssessmentPack(pairId),
      api.getLatestWeeklyAssessment(pairId),
      api.getWeeklyAssessmentTrend(pairId),
    ])

    pack.value = packRes.status === 'fulfilled' ? packRes.value : { items: [] }
    latest.value = latestRes.status === 'fulfilled' ? latestRes.value : null
    trend.value = trendRes.status === 'fulfilled' ? trendRes.value : { trend_points: [] }
  } catch (e) {
    showToast(e.message || '体检题目没加载出来，请稍后再试')
  } finally {
    loading.value = false
  }
}

async function submitAssessment() {
  if (!canSubmit.value || submitting.value) return

  submitting.value = true
  try {
    const payload = {
      answers: questions.value.map((item) => answers.value[item.item_id]),
    }

    if (experienceMode.value.isDemoMode) {
      latest.value = {
        event_id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
        submitted_at: new Date().toISOString(),
        total_score: Math.round(payload.answers.reduce((sum, item) => sum + Number(item.score || 0), 0) / payload.answers.length),
        scope: isSoloScope.value ? 'solo' : 'pair',
        change_summary: isSoloScope.value
          ? '这次更像一次自我整理，先盯住最低的一两维，不用急着一次改很多。'
          : '比上一轮顺一点，继续按现在的节奏来。',
        dimension_scores: cloneDemo(demoFixture.assessmentLatest.dimension_scores),
      }
      trend.value = {
        ...cloneDemo(demoFixture.assessmentTrend),
        latest_score: latest.value.total_score,
        trend_points: [
          ...cloneDemo(demoFixture.assessmentTrend.trend_points).slice(-3),
          {
            event_id: latest.value.event_id,
            submitted_at: latest.value.submitted_at,
            total_score: latest.value.total_score,
            scope: latest.value.scope,
            change_summary: latest.value.change_summary,
            dimension_scores: [],
          },
        ],
      }
    } else {
      const pairId = currentPairId()
      latest.value = await api.submitWeeklyAssessment(pairId, payload)
      trend.value = await api.getWeeklyAssessmentTrend(pairId)
    }
    submitted.value = true
  } catch (e) {
    showToast(e.message || '这次体检没提交成功，请稍后再试')
  } finally {
    submitting.value = false
  }
}

function restartAssessment() {
  requestAssessmentReload()
}

function reloadPack() {
  requestAssessmentReload()
}

function requestAssessmentReload() {
  if (loading.value) return
  const remainingSeconds = assessmentPackGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`体检刷新得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  assessmentPackGuard.markRun()
  loadAssessment()
}
</script>

<style scoped>
.health-page {
  padding-bottom: 28px;
}

.health-lead {
  margin-top: 10px;
  color: var(--ink-soft);
  line-height: 1.72;
}

.health-scope-card {
  display: grid;
  gap: 16px;
}

.health-scope-card--compact {
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
}

.health-scope-card--compact .health-scope-grid {
  grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
}

.health-scope-card--compact .hero-actions {
  justify-content: end;
}


.health-scope-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.health-scope-option {
  display: grid;
  gap: 6px;
  text-align: left;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(74, 61, 50, 0.12);
  background: rgba(255, 250, 244, 0.72);
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.health-scope-option span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 700;
}

.health-scope-option strong {
  color: var(--ink-strong);
  font-size: 16px;
}

.health-scope-option.active {
  border-color: var(--seal-deep);
  background: linear-gradient(180deg, rgba(240, 213, 184, 0.24), rgba(255, 250, 244, 0.94));
  transform: translateY(-1px);
}

.health-scope-current {
  color: var(--ink-soft);
  font-size: 13px;
}

.health-scope-current--inline {
  margin-top: 8px;
}

.health-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.health-side {
  display: grid;
  gap: 16px;
  align-content: start;
}

.health-question-wrap {
  display: grid;
  gap: 16px;
}

.health-question-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 20px;
}

.health-question-actions--single {
  grid-template-columns: minmax(0, 1fr);
}

.health-question-actions__button {
  width: 100%;
  min-width: 120px;
  min-height: 48px;
  padding: 0 20px;
  border-radius: 999px;
  font-size: 15px;
  justify-content: center;
}

.health-progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 700;
}

.health-question {
  font-family: var(--font-serif);
  font-size: 22px;
  line-height: 1.5;
}

.stack-item.active {
  border: 2px solid var(--seal-deep);
  background: linear-gradient(180deg, rgba(240, 213, 184, 0.3), rgba(255, 250, 244, 0.94));
}

.health-result {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.health-result-hero {
  display: grid;
  grid-template-columns: 148px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
  padding: 18px;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 14% 16%, rgba(255, 229, 221, 0.56), transparent 36%),
    linear-gradient(180deg, rgba(255, 252, 247, 0.88), rgba(255, 248, 242, 0.72));
  min-width: 0;
  overflow: hidden;
}

.health-result-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.health-result-copy .eyebrow {
  margin: 0;
}

.result-ring {
  position: relative;
  width: 122px;
  height: 122px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, rgba(255, 252, 247, 0.96) 0 56%, transparent 57%),
    conic-gradient(var(--seal) 0 var(--result-score-deg, 0deg), rgba(232, 240, 244, 0.88) var(--result-score-deg, 0deg) 360deg);
  display: grid;
  gap: 0;
  place-items: center;
  align-content: center;
  margin: 12px auto 0;
  box-shadow: 0 16px 32px rgba(170, 77, 51, 0.12);
}

.health-result-hero .result-ring {
  margin: 0 auto;
}

.result-ring span {
  font-size: 36px;
  font-weight: 700;
  color: var(--seal-deep);
  font-family: var(--font-serif);
  line-height: 1;
}

.result-ring em {
  margin-bottom: 2px;
  color: var(--ink-faint);
  font-size: 11px;
  font-style: normal;
  font-weight: 900;
}

.result-ring b {
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 800;
}

.health-result-title,
.health-result-note,
.health-result-source {
  text-align: left;
}

.health-result-title {
  font-family: var(--font-serif);
  font-size: 22px;
}

.health-result-note,
.health-result-source {
  color: var(--ink-soft);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.health-result-source {
  margin: -4px 0 0;
  font-size: 13px;
}

.health-result-note--stable {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 250, 244, 0.7);
}

.health-result-actions {
  justify-content: center;
}

.health-result-visuals {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
  gap: 14px;
  min-width: 0;
}

.health-visual-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(74, 61, 50, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(255, 250, 244, 0.72);
  min-width: 0;
}

.health-visual-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.health-visual-card__head span {
  color: var(--ink);
  font-weight: 900;
}

.health-visual-card__head strong {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 28px;
}

.health-radar-layout {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.health-radar {
  width: 100%;
  overflow: visible;
}

.health-radar__grid {
  fill: rgba(255, 252, 248, 0.74);
  stroke: rgba(68, 52, 40, 0.13);
}

.health-radar__grid--inner {
  fill: rgba(232, 240, 244, 0.26);
}

.health-radar__axis {
  stroke: rgba(68, 52, 40, 0.1);
}

.health-radar__shape {
  fill: rgba(215, 104, 72, 0.18);
  stroke: var(--seal);
  stroke-width: 3;
  stroke-linejoin: round;
}

.health-radar__dot {
  fill: var(--sky-deep);
  stroke: #fffdf9;
  stroke-width: 2;
}

.health-radar__label,
.health-radar__value,
.health-radar__scale {
  font-family: var(--font-sans);
  font-weight: 800;
  pointer-events: none;
}

.health-radar__label {
  fill: var(--ink-soft);
  font-size: 11px;
}

.health-radar__value {
  fill: var(--seal-deep);
  font-size: 12px;
}

.health-radar__scale {
  fill: rgba(108, 99, 89, 0.56);
  font-size: 10px;
}

.health-radar-list {
  display: grid;
  gap: 8px;
}

.health-radar-list p,
.health-radar-list small,
.health-visual-note {
  margin: 0;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.health-radar-list small {
  color: var(--seal-deep);
  font-weight: 900;
}

.health-radar-list span {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  min-height: 26px;
  align-items: center;
  padding: 0 10px;
  border: 1px solid rgba(74, 61, 50, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--ink-soft);
  font-size: 12px;
}

.health-radar-list strong {
  color: var(--seal-deep);
}

.health-line-chart {
  width: 100%;
  height: 150px;
}

.health-line-chart__grid {
  fill: none;
  stroke: rgba(68, 52, 40, 0.08);
  stroke-dasharray: 4 8;
}

.health-line-chart__path {
  fill: none;
  stroke: var(--seal);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.health-line-chart__dot {
  fill: #fffdf9;
  stroke: var(--seal);
  stroke-width: 3;
}

.health-line-chart__value {
  fill: var(--seal-deep);
  font-size: 11px;
  font-weight: 900;
  pointer-events: none;
}

.health-line-chart__axis {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--ink-faint);
  font-size: 11px;
}

.health-dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.health-dimension-card {
  padding: 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 250, 244, 0.72);
}

.health-dimension-card span {
  display: block;
  color: var(--ink-faint);
  font-size: 12px;
  margin-bottom: 8px;
}

.health-dimension-card strong {
  font-size: 24px;
  font-family: var(--font-serif);
  color: var(--seal-deep);
}

.health-dimension-meter {
  height: 7px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(232, 240, 244, 0.86);
}

.health-dimension-meter i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--seal), var(--sky-deep));
}

.health-suggestions {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 250, 244, 0.72);
}

.plain-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.health-trend-list {
  display: grid;
  gap: 10px;
}

.health-trend-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 250, 244, 0.72);
}

.health-trend-item span {
  color: var(--ink-faint);
  font-size: 13px;
}

.health-trend-item strong {
  color: var(--seal-deep);
  font-family: var(--font-serif);
}

@media (max-width: 900px) {
  .health-layout,
  .health-result-visuals {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .health-scope-grid,
  .health-dimension-grid,
  .health-result-hero,
  .health-radar-layout,
  .health-scope-card--compact {
    grid-template-columns: 1fr;
  }

  .result-ring {
    margin-top: 0;
  }

  .health-result-title,
  .health-result-note,
  .health-result-source {
    text-align: center;
  }

  .health-question-actions {
    grid-template-columns: 1fr;
  }
}
</style>

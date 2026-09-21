<template>
  <div class="home-page">
    <section class="home-dossier">
      <div class="dossier-copy">
        <div class="dossier-stamp">
          <FolderHeart :size="28" style="color: var(--seal)" />
          <span>今天的记录</span>
        </div>
        <p class="eyebrow">首页</p>
        <h2>
          <span class="home-dossier__dynamic-title">{{ heroHeadline }}</span>
        </h2>
        <div class="hero-actions hero-actions--primary">
          <button class="btn btn-primary" @click="$router.push(primaryAction.route)">
            <component :is="primaryActionIcon" :size="16" /> {{ primaryAction.buttonLabel }}
          </button>
          <button class="btn btn-secondary" @click="$router.push('/alignment')">
            {{ alignmentEntryLabel }} <ChevronRight :size="16" />
          </button>
        </div>
        <div class="hero-subactions">
          <button class="hero-subactions__link" @click="$router.push('/chat')">聊一聊</button>
          <button class="hero-subactions__link" @click="$router.push('/message-simulation')">发前看看</button>
          <button class="hero-subactions__link" @click="$router.push('/repair-protocol')">缓和建议</button>
          <button class="hero-subactions__link" @click="$router.push('/challenges')">今日安排</button>
          <button class="hero-subactions__link" @click="$router.push('/timeline')">关系日历</button>
        </div>
      </div>

      <div class="dossier-ledger" aria-label="今日摘要">
        <label v-if="relationshipOptions.length" class="relationship-switcher">
          <span>当前关系</span>
          <select :value="selectedRelationshipId" @change="handleRelationshipSelect">
            <option
              v-for="option in relationshipOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
        <div class="home-metrics" aria-label="关系状态摘要">
          <div class="metric-item metric-item--warm">
            <span style="display:flex; align-items:center; gap: 4px;"><CalendarDays :size="14" /> 连续记录</span>
            <strong>{{ streakDays }} 天</strong>
          </div>
          <div class="metric-item metric-item--moss">
            <span style="display:flex; align-items:center; gap: 4px;"><UserCheck :size="14" /> 我的状态</span>
            <strong>{{ myDone ? '已记录' : '未记录' }}</strong>
          </div>
          <div class="metric-item metric-item--sky">
            <span style="display:flex; align-items:center; gap: 4px;"><Users :size="14" /> {{ partnerMetricLabel }}</span>
            <strong>{{ partnerMetricValue }}</strong>
          </div>
          <div class="metric-item metric-item--amber">
            <span style="display:flex; align-items:center; gap: 4px;"><Activity :size="14" /> {{ signalMetricLabel }}</span>
            <strong>{{ signalMetricValue }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="home-analytics-strip" aria-label="关系数据概览">
      <article class="home-chart-card home-chart-card--trend">
        <div class="card-header">
          <div>
            <p class="eyebrow">30 天变化</p>
            <h3>最近走势</h3>
          </div>
          <span class="home-chart-card__badge">{{ homeTrendBadge }}</span>
        </div>
        <template v-if="hasHomeTrendData">
          <svg class="home-line-chart" viewBox="0 0 360 150" role="img" aria-label="最近三十天关系走势">
            <path class="home-line-chart__grid" d="M28 36 H332 M28 76 H332 M28 116 H332" />
            <path class="home-line-chart__axis" d="M28 126 H332" />
            <polyline :points="homeTrendPolyline" class="home-line-chart__line" />
            <circle
              v-for="point in homeTrendPoints"
              :key="point.label"
              :cx="point.x"
              :cy="point.y"
              r="4.5"
              class="home-line-chart__dot"
            />
            <text
              v-for="point in homeTrendPoints"
              :key="`${point.label}-score`"
              :x="point.x"
              :y="point.labelY"
              text-anchor="middle"
              class="home-line-chart__value"
            >{{ point.score }}</text>
          </svg>
          <div class="home-chart-axis">
            <span
              v-for="point in homeTrendPoints"
              :key="point.label"
              :style="{ left: `${point.axisX}%` }"
            >{{ point.label }}</span>
          </div>
        </template>
        <div v-else class="home-chart-empty">
          <strong>还没有趋势数据</strong>
          <span>多记几次日常，这里就会画出你们的心情走势图啦~</span>
        </div>
      </article>

      <article class="home-chart-card home-chart-card--radar">
        <div class="card-header">
          <div>
            <p class="eyebrow">关系五边形</p>
            <h3>五项关系状态</h3>
          </div>
          <span class="home-chart-card__badge home-chart-card__badge--blue">{{ homeRadarBadge }}</span>
        </div>
        <div v-if="hasHomeRadarData" class="home-radar-layout">
          <svg class="home-radar-chart" viewBox="0 0 240 230" role="img" :aria-label="homeRadarAriaLabel">
            <polygon points="110,24 192,84 161,180 59,180 28,84" class="home-radar-chart__grid" />
            <polygon points="110,58 160,95 141,154 79,154 60,95" class="home-radar-chart__grid home-radar-chart__grid--inner" />
            <text x="116" y="35" class="home-radar-chart__scale">100</text>
            <text x="116" y="64" class="home-radar-chart__scale">70</text>
            <line
              v-for="axis in homeRadarAxes"
              :key="axis.label"
              x1="110"
              y1="110"
              :x2="axis.x"
              :y2="axis.y"
              class="home-radar-chart__axis"
            />
            <polygon :points="homeRadarPolygon" class="home-radar-chart__shape" />
            <g v-for="axis in homeRadarAxes" :key="`${axis.label}-point`">
              <circle
                :cx="axis.valueX"
                :cy="axis.valueY"
                r="4"
                class="home-radar-chart__dot"
              />
              <text
                :x="axis.valueLabelX"
                :y="axis.valueLabelY"
                :text-anchor="axis.valueTextAnchor"
                class="home-radar-chart__value"
              >{{ axis.value }}</text>
              <text
                :x="axis.labelX"
                :y="axis.labelY"
                :text-anchor="axis.labelAnchor"
                class="home-radar-chart__label"
              >{{ axis.label }}</text>
            </g>
          </svg>
          <div class="home-radar-list">
            <span v-for="axis in homeRadarAxes" :key="axis.label">
              {{ axis.label }} <strong>{{ axis.value }}</strong>
            </span>
          </div>
        </div>
        <div v-else class="home-chart-empty">
          <strong>还没有维度数据</strong>
          <span>做过一次小体检或有了简报后，就能看到你们的关系雷达图啦~</span>
        </div>
      </article>
    </section>

    <div class="home-ledger">
      <div class="home-ledger__main">
        <section class="archive-panel">
          <div class="card-header">
            <div>
              <p class="eyebrow">{{ homeTaskScopeTab === 'today' ? '今日安排' : '明日安排' }}</p>
              <h3>{{ homeTaskScopeTab === 'today' ? '今天先做这些' : '明天先看这些' }}</h3>
            </div>
            <div class="home-task-switch" role="group" aria-label="首页安排切换">
              <button
                class="home-task-switch__item"
                :class="{ active: homeTaskScopeTab === 'today' }"
              :aria-pressed="homeTaskScopeTab === 'today'"
                type="button"
                @click="setHomeTaskScope('today')"
              >
                今天
              </button>
              <button
                class="home-task-switch__item"
                :class="{ active: homeTaskScopeTab === 'tomorrow' }"
              :aria-pressed="homeTaskScopeTab === 'tomorrow'"
                type="button"
                @click="setHomeTaskScope('tomorrow')"
              >
                明天
              </button>
            </div>
          </div>
          <div v-if="displayHomeDailyNote" class="home-daily-note">
            <span class="home-daily-note__text">“{{ displayHomeDailyNote }}”</span>
            <button
              class="btn-note-rotate"
              type="button"
              title="换一句每日寄语"
              @click="rotateHomeDailyNote"
            >
              <RotateCcw :size="12" />
              <span>换一句</span>
            </button>
          </div>
          <div v-if="homeTaskLoading" class="home-list home-list--empty">正在加载安排…</div>
          <div v-else-if="scheduleError" class="home-list home-list--empty" role="alert">{{ scheduleError }} <button class="btn btn-ghost btn-sm" @click="loadHomeTasks">重试</button></div>
            <div v-else-if="!homeTaskItems.length" class="home-list home-list--empty">{{ homeTaskScopeTab === 'today' ? '今天还没有安排' : '明天还没有安排' }}</div>
            <div v-else class="home-list home-list--scroll">
            <article
              v-for="item in homeTaskItems"
              :key="item.id || item.label"
              class="home-list__item"
            >
              <strong>{{ item.title || item.label }}</strong>
              <span v-if="item.status === 'completed'" class="pill pill--soft">已完成</span>
              <p>{{ item.description || item.note }}</p>
              <button v-if="item.id && homeTaskScopeTab === 'today'" class="btn btn-ghost btn-sm" type="button" @click="resultTask = item">更新结果</button>
            </article>
          </div>
          <div class="hero-actions home-task-actions">
              <button class="btn btn-secondary btn-sm" type="button" :disabled="homeTaskLoading || Boolean(scheduleError)" @click="openScheduleAgent()">{{ homeTaskScopeTab === 'today' ? '让 AI 帮我选一件' : '和 AI 商量明天' }}</button>
            <button
              class="btn btn-ghost btn-sm"
              type="button"
              @click="$router.push({ path: '/challenges', query: { pair_id: userStore.activePairId, scope: homeTaskScopeTab } })"
            >
              {{ homeTaskScopeTab === 'today' ? '打开今天安排' : '打开明天安排' }}
            </button>
          </div>
        </section>

        <section class="archive-panel" aria-label="最近节点">
          <div class="card-header">
            <div>
              <p class="eyebrow">最近节点</p>
              <h3>最近发生了什么</h3>
            </div>
            <button class="btn btn-ghost btn-sm" @click="$router.push('/milestones')">查看全部</button>
          </div>
          <div class="home-list">
            <article
              v-for="item in homeOverview.milestoneItems"
              :key="item.label"
              class="home-list__item home-list__item--soft"
            >
              <strong>{{ item.label }}</strong>
              <p>{{ item.note }}</p>
            </article>
          </div>
        </section>
      </div>

      <aside class="home-ledger__side">
        <section v-if="showRelationshipTree" class="archive-panel life-tree-panel">
          <div class="card-header">
            <p class="eyebrow">关系树</p>
          </div>
          <RelationshipTree :nodes="treeEnergyNodes" :collecting-key="collectingEnergyKey" :feedback="energyFeedback" :resting="treeDecayPoints > 0" @collect="handleCollectEnergyNode" />
          <div class="tree-progress-head">
            <span>成长值</span>
            <strong>{{ treeProgress }}%</strong>
          </div>
          <div class="tree-progress" role="progressbar" aria-label="关系树成长进度" :aria-valuenow="treeProgress" aria-valuemin="0" aria-valuemax="100">
            <span :style="{ width: `${treeProgress}%` }"></span>
          </div>
          <div class="tree-leaves">
            <div v-for="leaf in treeLeaves" :key="leaf.label" class="tree-leaf">
              <span>{{ leaf.label }}</span>
              <strong>{{ leaf.value }}</strong>
            </div>
          </div>
        </section>
        <section v-else class="archive-panel life-tree-panel life-tree-panel--solo">
          <div class="card-header">
            <div>
              <p class="eyebrow">{{ relationSectionLabel }}</p>
              <h3>{{ sidePanelTitle }}</h3>
            </div>
          </div>
            <div class="tree-leaves tree-leaves--solo">
              <div
                v-for="item in sidePanelLeafItems"
                :key="item.label"
                class="tree-leaf"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
          </div>
          <div class="tree-actions">
            <button v-if="showSidePrimaryAction" class="btn btn-secondary btn-sm" @click="$router.push(primaryAction.route)">{{ primaryAction.label }}</button>
            <button class="btn btn-ghost btn-sm" @click="$router.push(sidePanelSecondaryAction.route)">{{ sidePanelSecondaryAction.label }}</button>
          </div>
        </section>
      </aside>
    </div>
    <TaskResultDialog v-if="resultTask" :task="resultTask" :pair-id="userStore.activePairId" :date="scheduleDate(homeTaskScopeTab)" @close="resultTask = null" @saved="loadHomeTasks" @analyze="scheduleContext = $event" />
    <ContextAgentDialog v-if="scheduleContext" :context="scheduleContext" @close="scheduleContext = null" />
  </div>
</template>

<script setup>
import RelationshipTree from '@/components/RelationshipTree.vue'
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import TaskResultDialog from '@/components/TaskResultDialog.vue'
import { buildDemoSchedule, buildScheduleContext, createLatestRequest, scheduleDate, demoScheduleCache } from '@/utils/taskSchedule'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { FolderHeart, PenLine, FileText, Handshake, ChevronRight, CalendarDays, UserCheck, Users, Activity, RotateCcw } from 'lucide-vue-next'
import { clampDailyNote, getNextDailyNote, DAILY_NOTE_CANDIDATES } from '@/utils/dailyNotes'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { useHomeStore } from '@/stores/home'
import { useUserStore } from '@/stores/user'
import { resolveHomeRelationshipView } from '@/utils/homeMode'
import { buildHomeOverview } from '@/utils/homeOverview'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { resolveRelationshipDisplayPair } from '@/utils/relationshipDisplay'
import { normalizeEnergyNodes } from '@/utils/relationshipTreeEnergy'
import { getPartnerDisplayName } from '@/utils/relationshipSpaces'

function isoDate(offset = 0) {
  const now = new Date()
  const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
  const pad = (value) => String(value).padStart(2, '0')
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`
}

function normalizeScore(value) {
  const score = Number(value)
  if (!Number.isFinite(score)) return null
  return Math.min(100, Math.max(0, Math.round(score)))
}

function scoreComfortText(score) {
  if (score >= 75) return '还算平稳'
  if (score >= 60) return '可以留意'
  if (score >= 40) return '有一点紧'
  return '先慢一点'
}

function pairOptionLabel(pair) {
  return getPartnerDisplayName(pair)
}

function buildDemoHomeTaskPayload(scope = 'today') {
  const saved = demoScheduleCache.read({ owner: userStore.me?.id || 'sample', pairId: userStore.activePairId, date: scheduleDate(scope) })
  if (saved) return saved
  const payload = { ...buildDemoSchedule(demoFixture.tasks, scope) }
  demoScheduleCache.save({ owner: userStore.me?.id || 'sample', pairId: userStore.activePairId, date: scheduleDate(scope) }, payload)
  return payload
}

const homeStore = useHomeStore()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const collectingEnergyKey = ref('')
const energyFeedback = ref(null)
let energyFeedbackTimer = null
let energyRequestVersion = 0
function clearEnergyFeedback() {
  energyRequestVersion++
  collectingEnergyKey.value = ''
  energyFeedback.value = null
  clearTimeout(energyFeedbackTimer)
}
onBeforeUnmount(clearEnergyFeedback)
watch(() => [userStore.activePairId, userStore.token, userStore.me?.id], clearEnergyFeedback, { flush: 'sync' })
const homeTaskScopeTab = ref('today')
const homeTaskPayload = ref({ tasks: [] })
const homeTaskLoading = ref(false)
const customHomeDailyNote = ref('')

const displayHomeDailyNote = computed(() => {
  if (customHomeDailyNote.value) {
    return clampDailyNote(customHomeDailyNote.value)
  }
  const sourceNote = homeTaskScopeTab.value === 'tomorrow'
    ? (homeTaskPayload.value.planning_note || homeTaskPayload.value.daily_note)
    : (homeTaskPayload.value.daily_note || homeStore.dailyNote)
  return clampDailyNote(sourceNote || DAILY_NOTE_CANDIDATES[0])
})

function rotateHomeDailyNote() {
  const next = getNextDailyNote(displayHomeDailyNote.value)
  customHomeDailyNote.value = next
}

const streakDays = computed(() => homeStore.snapshot?.streak?.streak || 0)
const myDone = computed(() => homeStore.snapshot?.todayStatus?.my_done || false)
const partnerDone = computed(() => homeStore.snapshot?.todayStatus?.partner_done || false)
const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const relationshipDisplayPair = computed(() => resolveRelationshipDisplayPair({
  activePair: userStore.activePair,
  currentPair: userStore.currentPair,
}))
const relationshipView = computed(() => resolveHomeRelationshipView({
  currentPair: relationshipDisplayPair.value,
  partnerName: userStore.partnerName,
}))
const showRelationshipTree = computed(() => relationshipView.value.showRelationshipTree)
const relationshipOptions = computed(() => {
  const pairs = Array.isArray(userStore.pairs) ? userStore.pairs : []
  const activePairs = pairs.filter((pair) => pair?.status === 'active')
  const source = activePairs.length ? activePairs : pairs
  return source
    .filter((pair) => pair?.id)
    .map((pair) => ({
      id: pair.id,
      label: pairOptionLabel(pair),
    }))
})
const selectedRelationshipId = computed(() =>
  userStore.currentPair?.id || userStore.activePairId || relationshipOptions.value[0]?.id || ''
)
const crisisLevel = computed(() => homeStore.crisis?.crisis_level || 'none')
const scorePercent = computed(() => {
  const realScore = normalizeScore(
    homeStore.crisis?.health_score
      ?? homeStore.crisis?.overall_health_score
      ?? homeStore.snapshot?.todayStatus?.health_score
      ?? homeStore.snapshot?.todayStatus?.relationship_score,
  )
  if (realScore !== null) return realScore

  const map = { none: 76, mild: 55, moderate: 35, severe: 15 }
  return map[crisisLevel.value] || 76
})
const relationshipFeelingScore = computed(() => Math.round(scorePercent.value))

const crisisLabel = computed(() => {
  const map = { none: '平稳', mild: '可以留意', moderate: '先慢一点', severe: '先照顾自己' }
  return map[crisisLevel.value] || '平稳'
})
const crisisComfortLabel = computed(() => {
  const realScore = normalizeScore(
    homeStore.crisis?.health_score
      ?? homeStore.crisis?.overall_health_score
      ?? homeStore.snapshot?.todayStatus?.health_score
      ?? homeStore.snapshot?.todayStatus?.relationship_score,
  )
  if (realScore !== null) return scoreComfortText(realScore)

  const map = { none: '还算平稳', mild: '有一点紧', moderate: '先慢一点', severe: '先照顾自己' }
  return map[crisisLevel.value] || '还算平稳'
})
const relationSectionLabel = computed(() => relationshipView.value.sectionLabel)
const partnerMetricLabel = computed(() => relationshipView.value.partnerMetricLabel)
const partnerMetricValue = computed(() => {
  if (relationshipView.value.kind === 'paired') return partnerDone.value ? '已记录' : '待同步'
  if (relationshipView.value.kind === 'pending') return '待加入'
  return '单人整理'
})
const signalMetricLabel = computed(() => relationshipView.value.signalMetricLabel)
const signalMetricValue = computed(() => relationshipView.value.kind === 'paired' ? crisisLabel.value : '先写自己')
const sidePanelTitle = computed(() => relationshipView.value.sideCardTitle)
const homeOverview = computed(() => buildHomeOverview({
  relationshipView: relationshipView.value,
  snapshot: homeStore.snapshot,
  crisis: homeStore.crisis,
  tasks: homeStore.tasks,
  milestones: homeStore.milestones,
}))
const primaryAction = computed(() => homeOverview.value.primaryAction || {
  label: '去写今天',
  buttonLabel: '开始今日记录',
  route: '/checkin',
  slipLabel: '先写下今天发生的事',
  actionKind: 'checkin',
})
const primaryActionIcon = computed(() => {
  if (primaryAction.value.route === '/report') return FileText
  if (primaryAction.value.route === '/pair') return Handshake
  return PenLine
})
const isPrimaryCheckinAction = computed(() => primaryAction.value.route === '/checkin')
const showSidePrimaryAction = computed(() => !isPrimaryCheckinAction.value)
const alignmentEntryLabel = computed(() => {
  if (experienceMode.value.isDemoMode) return '看双视角样例'
  if (experienceMode.value.canUseDualPerspective) return '看双视角'
  return '双视角'
})
const heroHeadline = computed(() => {
  if (primaryAction.value.actionKind === 'report') {
    if (primaryAction.value.reportState === 'pending') {
      return primaryAction.value.isSoloReport ? '你的个人简报正在整理中' : '这期简报正在整理中'
    }
    return primaryAction.value.isSoloReport ? '你的个人简报可以看了' : '这期简报可以看了'
  }
  if (primaryAction.value.actionKind === 'pair') {
    return relationshipView.value.kind === 'pending' ? '先把邀请发出去' : '先看看关系状态'
  }
  if (primaryAction.value.actionKind === 'task') return '先做这一步'
  return relationshipView.value.kind === 'paired' ? '先记下今天的情况' : '先记下今天发生的事'
})
const homeTaskItems = computed(() => {
  const items = homeTaskPayload.value.tasks || []
  if (items.length) return items.slice(0, 6)
  return homeTaskScopeTab.value === 'today' && !userStore.activePairId ? homeOverview.value.todoItems || [] : []
})
const sidePanelLeafItems = computed(() => {
  if (relationshipView.value.kind === 'pending') {
    return [
      { label: '现在优先做', value: '把邀请码发出去' },
      { label: '之后再做', value: '等对方加入后再开始' },
    ]
  }

  if (primaryAction.value.actionKind === 'report') {
    return [
      {
        label: '现在优先做',
        value: primaryAction.value.reportState === 'pending' ? '看简报整理进度' : primaryAction.value.buttonLabel,
      },
      {
        label: '之后再做',
        value: relationshipView.value.kind === 'paired' ? '再决定要不要继续聊' : '再决定要不要补充记录',
      },
    ]
  }

  if (primaryAction.value.actionKind === 'task') {
    return [
      { label: '现在优先做', value: primaryAction.value.buttonLabel },
      { label: '之后再做', value: '做完这一步再看后面' },
    ]
  }

  return [
    {
      label: '现在优先做',
      value: relationshipView.value.kind === 'paired' ? '先写下今天的情况' : '先写下今天的事',
    },
    {
      label: '之后再做',
      value: relationshipView.value.kind === 'paired' ? '再去看关系状态' : '再整理成简报',
    },
  ]
})
const sidePanelSecondaryAction = computed(() => {
  if (relationshipView.value.kind === 'pending') {
    return {
      label: '先写今天',
      route: '/checkin',
    }
  }

  if (primaryAction.value.actionKind === 'report') {
    return {
      label: '关系日历',
      route: '/timeline',
    }
  }

  return {
    label: relationshipView.value.kind === 'solo' ? '建立关系' : '去关系管理',
    route: '/pair',
  }
})
const TREE_STAGE_META = {
  seed: {
    label: '刚破冰',
    title: '愿意开始，就是好事',
    explanation: '肯把今天发生的事记下来，这段关系就算开了个头。',
  },
  sprout: {
    label: '开始熟悉',
    title: '聊天没那么拘着了',
    explanation: '开始愿意多说一句近况，也会顺手多问一句对方。',
  },
  sapling: {
    label: '有来有往',
    title: '不是一个人在使劲了',
    explanation: '开始有来有往，关系在升温。',
  },
  tree: {
    label: '话说开了',
    title: '原来别着的话，开始能说出来了',
    explanation: '不一定每次都很顺，但已经能把在意的事讲清楚一点。',
  },
  big_tree: {
    label: '相处顺了',
    title: '最近没那么拧巴了',
    explanation: '知道什么时候该聊，什么时候该缓一缓，日子会过得更舒服。',
  },
  forest: {
    label: '越来越对味',
    title: '很多事，不用多说也懂一点了',
    explanation: '不是天天热闹，但相处起来越来越舒服，这种感觉很难得。',
  },
}
const treeStageKey = computed(() => String(homeStore.tree?.level || '').toLowerCase())
const treeStageMeta = computed(() => TREE_STAGE_META[treeStageKey.value] || TREE_STAGE_META.seed)
const treeStageLabel = computed(() => homeStore.tree?.stage_label || treeStageMeta.value.label)
const treeProgress = computed(() => Math.min(100, Math.max(0, Number(homeStore.tree?.display_progress_percent ?? homeStore.tree?.progress_percent ?? 0))))
const treeDecayPoints = computed(() => Math.max(0, Number(homeStore.tree?.decay_points || 0)))
const treeStageTitle = computed(() => homeStore.tree?.stage_title || treeStageMeta.value.title)
const treeEnergyNodes = computed(() => normalizeEnergyNodes(homeStore.tree?.energy_nodes || homeStore.tree?.energy_bubbles || []))
const treeLeaves = computed(() => homeStore.tree?.leaves?.length ? homeStore.tree.leaves : [
  { label: '当时的话', value: '0 条', note: '先记录一句真实发生的话。' },
  { label: '缓和', value: '0 次', note: '做完小行动后会长出新枝叶。' },
])

const DEMO_HOME_TREND_POINTS = [
  { label: '30天前', x: 28, y: 112, score: 58 },
  { label: '24天前', x: 88.8, y: 98, score: 63 },
  { label: '18天前', x: 149.6, y: 104, score: 61 },
  { label: '12天前', x: 210.4, y: 76, score: 72 },
  { label: '6天前', x: 271.2, y: 68, score: 75 },
  { label: '今天', x: 332, y: 46, score: 82 },
]
DEMO_HOME_TREND_POINTS.forEach((point) => {
  point.labelY = Math.max(18, point.y - 10)
  point.axisX = Number(((point.x / 360) * 100).toFixed(2))
})

const DEMO_HOME_RADAR_AXES = [
  { label: '表达', x: 110, y: 24, value: 72 },
  { label: '信任', x: 192, y: 84, value: 64 },
  { label: '缓和', x: 161, y: 180, value: 70 },
  { label: '节奏', x: 59, y: 180, value: 58 },
  { label: '活力', x: 28, y: 84, value: 76 },
]

const homeTrendPoints = computed(() => (experienceMode.value.isDemoMode ? DEMO_HOME_TREND_POINTS : []))
const hasHomeTrendData = computed(() => homeTrendPoints.value.length > 0)
const homeTrendPolyline = computed(() => homeTrendPoints.value.map((point) => `${point.x},${point.y}`).join(' '))
const homeTrendBadge = computed(() => (hasHomeTrendData.value ? '样例趋势' : '暂无数据'))
const homeRadarAxes = computed(() => {
  if (!experienceMode.value.isDemoMode) return []
  const center = { x: 110, y: 110 }
  return DEMO_HOME_RADAR_AXES.map((axis) => {
    const ratio = axis.value / 100
    const dx = axis.x - center.x
    const dy = axis.y - center.y
    const length = Math.hypot(dx, dy) || 1
    const unitX = dx / length
    const unitY = dy / length
    return {
      ...axis,
      valueX: Number((center.x + (axis.x - center.x) * ratio).toFixed(1)),
      valueY: Number((center.y + (axis.y - center.y) * ratio).toFixed(1)),
      valueLabelX: Number((center.x + dx * ratio + unitX * 12).toFixed(1)),
      valueLabelY: Number((center.y + dy * ratio + unitY * 12 + 4).toFixed(1)),
      valueTextAnchor: axis.x > 130 ? 'start' : axis.x < 90 ? 'end' : 'middle',
      labelX: Number((axis.x + unitX * 18).toFixed(1)),
      labelY: Number((axis.y + unitY * 18 + 4).toFixed(1)),
      labelAnchor: axis.x > 130 ? 'start' : axis.x < 90 ? 'end' : 'middle',
    }
  })
})
const hasHomeRadarData = computed(() => homeRadarAxes.value.length > 0)
const homeRadarPolygon = computed(() => homeRadarAxes.value.map((axis) => `${axis.valueX},${axis.valueY}`).join(' '))
const homeRadarAverage = computed(() => {
  const axes = homeRadarAxes.value
  if (!axes.length) return null
  return Math.round(axes.reduce((sum, axis) => sum + Number(axis.value || 0), 0) / axes.length)
})
const homeRadarBadge = computed(() => (hasHomeRadarData.value ? `${homeRadarAverage.value} / 100` : '暂无数据'))
const homeRadarAriaLabel = computed(() =>
  hasHomeRadarData.value
    ? `关系五边形，${homeRadarAxes.value.map((axis) => `${axis.label}${axis.value}分`).join('，')}`
    : '关系五边形，还没有维度数据'
)

function setHomeTaskScope(scope) {
  homeTaskScopeTab.value = scope === 'tomorrow' ? 'tomorrow' : 'today'
}

async function handleRelationshipSelect(event) {
  const pairId = String(event?.target?.value || '').trim()
  if (!pairId || pairId === selectedRelationshipId.value) return
  await userStore.switchPair(pairId)
}

async function loadHomeTasks() {
  const current = scheduleRequests.begin()
  const requestScope = homeTaskScopeTab.value
  const requestPair = userStore.activePairId
  homeTaskLoading.value = false
  scheduleError.value = ''
  homeTaskPayload.value = { tasks: [] }
  if (!(userStore.activePairId)) return
  if (userStore.isDemoMode) {
    homeTaskPayload.value = buildDemoHomeTaskPayload(requestScope)
    return
  }
  homeTaskLoading.value = true
  try {
    const result = await api.getDailyTasks(requestPair, { forDate: scheduleDate(requestScope), dateScope: requestScope })
    if (current()) homeTaskPayload.value = result
  } catch (error) {
    if (current()) scheduleError.value = error.message || '安排没加载出来，请重试'
  } finally {
    if (current()) homeTaskLoading.value = false
  }
}

async function handleCollectEnergyNode(node) {
  if (collectingEnergyKey.value || !node?.available || node.collected) return
  if (!userStore.hasActivePair || !userStore.activePairId) {
    showToast(featureUnavailableReason('pair-context', experienceMode.value))
    return
  }
  const request = ++energyRequestVersion
  const scope = userStore.activePairId
  collectingEnergyKey.value = node.key
  try {
    const updated = await homeStore.collectTreeEnergy(scope, node.key)
    if (request !== energyRequestVersion) return
    const points = Number(updated?.points_added ?? 0)
    if (points > 0) {
      clearTimeout(energyFeedbackTimer)
      energyFeedback.value = { key: node.key, points, id: request }
      energyFeedbackTimer = setTimeout(() => { energyFeedback.value = null }, 1400)
    }
  } catch (error) {
    if (request === energyRequestVersion) showToast(error.message || '这次没收成功，再试一次吧')
  } finally {
    if (request === energyRequestVersion) collectingEnergyKey.value = ''
  }
}

watch(
  () => [userStore.activePairId, homeTaskScopeTab.value],
  () => {
    customHomeDailyNote.value = ''
    loadHomeTasks()
  }
)

watch(
  () => userStore.activePairId,
  (pairId) => {
    homeStore.loadAll(pairId || null)
  }
)

onMounted(async () => {
  await homeStore.loadAll(userStore.activePairId || null)
  await loadHomeTasks()
})
const scheduleContext = ref(null)
const resultTask = ref(null)
const scheduleRequests = createLatestRequest()
const scheduleError = ref('')
function openScheduleAgent(task = null) {
  scheduleContext.value = buildScheduleContext(task ? [task] : homeTaskItems.value, {
    scope: homeTaskScopeTab.value, date: scheduleDate(homeTaskScopeTab.value), pairId: userStore.activePairId || null,
    isDemoMode: userStore.isDemoMode, single: Boolean(task),
  })
}
watch(() => [userStore.token, userStore.me?.id, userStore.activePairId, homeTaskScopeTab.value], () => {
  scheduleRequests.invalidate()
  scheduleContext.value = null
  resultTask.value = null
  homeTaskPayload.value = { tasks: [] }
  homeTaskLoading.value = false
}, { flush: 'sync' })
watch(() => [userStore.token, userStore.me?.id], () => loadHomeTasks())
onBeforeUnmount(() => scheduleRequests.invalidate())

</script>

<style scoped>
.home-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 28px;
}

.home-dossier {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 20px;
  align-items: stretch;
  margin-bottom: 16px;
  padding: 24px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 8% 10%, rgba(240, 213, 184, 0.4), transparent 28%),
    radial-gradient(circle at 88% 14%, rgba(223, 233, 221, 0.22), transparent 22%),
    linear-gradient(180deg, rgba(255, 252, 247, 0.95), rgba(246, 238, 229, 0.92));
  box-shadow: 0 18px 40px rgba(91, 67, 51, 0.07);
}

.home-dossier::before {
  content: "";
  position: absolute;
  left: 28px;
  top: 28px;
  width: 74px;
  height: 1px;
  background: linear-gradient(90deg, rgba(215, 104, 72, 0.48), rgba(215, 104, 72, 0));
}

.dossier-copy {
  position: relative;
  min-height: 220px;
  padding-right: 12px;
}

.dossier-stamp {
  position: absolute;
  top: -6px;
  right: 0;
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  border: 1px solid rgba(189, 75, 53, 0.42);
  border-radius: var(--radius-lg);
  color: var(--seal-deep);
  background: rgba(255, 251, 247, 0.54);
  backdrop-filter: blur(8px);
  transform: rotate(2deg);
  box-shadow: 0 12px 24px rgba(170, 77, 51, 0.08);
}

.dossier-stamp img {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
}

.dossier-stamp span {
  font-size: 11px;
  font-weight: 700;
}

.dossier-copy h2 {
  max-width: none;
  margin: 8px 0 10px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.24;
  text-wrap: pretty;
}

.hero-actions--primary {
  margin-top: 16px;
}

.hero-subactions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: center;
  margin-top: 12px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.hero-subactions__link {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 999px;
  background: rgba(255, 251, 247, 0.56);
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 600;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.hero-subactions__link:hover {
  transform: translateY(-1px);
  border-color: rgba(215, 104, 72, 0.22);
  background: rgba(255, 248, 243, 0.9);
}

.dossier-ledger {
  display: grid;
  gap: 10px;
  align-content: start;
  justify-items: end;
}

.relationship-switcher {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  width: min(220px, 100%);
  padding: 8px 10px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(232, 240, 244, 0.64), rgba(255, 251, 247, 0.86));
  box-shadow: 0 10px 24px rgba(91, 67, 51, 0.05);
}

.relationship-switcher span {
  color: var(--ink-faint);
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.relationship-switcher select {
  width: 100%;
  min-height: 32px;
  padding: 0 30px 0 10px;
  border: 1px solid rgba(67, 98, 115, 0.16);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 253, 250, 0.96), rgba(249, 245, 239, 0.92));
  color: var(--ink);
  font: inherit;
  font-size: 13px;
  font-weight: 800;
}

.dossier-slip,
.archive-panel,
.metric-item {
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 251, 247, 0.8);
}

.dossier-slip {
  padding: 16px;
  box-shadow: 0 10px 24px rgba(91, 67, 51, 0.05);
}

.temperature-slip {
  background:
    linear-gradient(180deg, rgba(255, 251, 247, 0.94), rgba(255, 248, 243, 0.88)),
    rgba(255, 251, 247, 0.8);
}

.temperature-slip__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 4px;
}

.temperature-slip span,
.metric-item span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 700;
}

.temperature-slip strong {
  display: block;
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 18px;
  line-height: 1.48;
}

.temperature-slip b {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 24px;
  line-height: 1;
}

.score-card__meta {
  display: none;
}

.home-metrics {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 7px;
  margin: 0;
}

.metric-item {
  position: relative;
  min-width: 0;
  min-height: 58px;
  padding: 10px 9px;
  overflow: visible;
  background: rgba(255, 251, 247, 0.74);
  box-shadow: 0 8px 18px rgba(91, 67, 51, 0.04);
}

.metric-item::before {
  content: "";
  position: absolute;
  left: 10px;
  top: 0;
  width: 22px;
  height: 3px;
  border-radius: 999px;
}

.metric-item--warm::before { background: var(--seal); }
.metric-item--moss::before { background: var(--moss); }
.metric-item--sky::before { background: var(--sky-deep); }
.metric-item--amber::before { background: var(--ochre); }

.metric-item--warm strong { color: var(--seal-deep); }
.metric-item--moss strong { color: var(--moss-deep); }
.metric-item--sky strong { color: var(--sky-deep); }
.metric-item--amber strong { color: var(--ochre); }

.metric-item--warm {
  background: linear-gradient(180deg, rgba(255, 246, 241, 0.92), rgba(255, 251, 247, 0.8));
}

.metric-item--moss {
  background: linear-gradient(180deg, rgba(239, 247, 250, 0.92), rgba(255, 251, 247, 0.8));
}

.metric-item--sky {
  background: linear-gradient(180deg, rgba(243, 248, 248, 0.92), rgba(255, 251, 247, 0.82));
}

.metric-item--amber {
  background: linear-gradient(180deg, rgba(250, 244, 234, 0.94), rgba(255, 251, 247, 0.82));
}

.metric-item strong {
  display: block;
  margin: 3px 0 0;
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.metric-item span {
  min-width: 0;
  white-space: nowrap;
}

.home-analytics-strip {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 14px;
  margin-bottom: 16px;
}

.home-chart-card {
  padding: 18px;
  border: 1px solid var(--border-strong);
  border-radius: 28px;
  background:
    radial-gradient(circle at 12% 0%, rgba(215, 104, 72, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(255, 253, 249, 0.92), rgba(248, 243, 237, 0.84));
  box-shadow: 0 12px 26px rgba(91, 67, 51, 0.045);
}

.home-chart-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(189, 75, 53, 0.2);
  border-radius: 999px;
  background: rgba(255, 248, 242, 0.86);
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 800;
}

.home-chart-card__badge--blue {
  border-color: rgba(67, 98, 115, 0.2);
  background: rgba(232, 240, 244, 0.9);
  color: var(--sky-deep);
}

.home-chart-empty {
  min-height: 190px;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
  color: var(--ink-faint);
  border: 1px dashed rgba(91, 67, 51, 0.18);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.56);
}

.home-chart-empty strong {
  color: var(--ink);
  font-size: 16px;
}

.home-chart-empty span {
  font-size: 13px;
}





























.home-line-chart {
  display: block;
  width: 100%;
  max-width: 420px;
  height: 150px;
  margin: 0 auto;
}

.home-line-chart__grid {
  fill: none;
  stroke: rgba(68, 52, 40, 0.08);
  stroke-dasharray: 4 8;
}

.home-line-chart__axis {
  fill: none;
  stroke: rgba(68, 52, 40, 0.18);
}

.home-line-chart__line {
  fill: none;
  stroke: url(#homeLineGradient);
}

.home-line-chart__line {
  stroke: var(--seal);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.home-line-chart__dot {
  fill: #fffdf9;
  stroke: var(--seal);
  stroke-width: 3;
}

.home-line-chart__value {
  fill: var(--seal-deep);
  font-size: 11px;
  font-weight: 900;
  pointer-events: none;
}

.home-chart-axis {
  position: relative;
  width: 100%;
  max-width: 420px;
  height: 20px;
  margin: 2px auto 0;
  color: var(--ink-faint);
  font-size: 10px;
  font-weight: 700;
}

.home-chart-axis span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  white-space: nowrap;
}

.home-radar-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.home-radar-chart {
  width: 100%;
  max-width: 210px;
  margin: 0 auto;
  overflow: visible;
}

.home-radar-chart__grid {
  fill: rgba(255, 252, 248, 0.76);
  stroke: rgba(68, 52, 40, 0.13);
}

.home-radar-chart__grid--inner {
  fill: rgba(232, 240, 244, 0.24);
}

.home-radar-chart__axis {
  stroke: rgba(68, 52, 40, 0.1);
}

.home-radar-chart__shape {
  fill: rgba(215, 104, 72, 0.18);
  stroke: var(--seal);
  stroke-width: 3;
  stroke-linejoin: round;
}

.home-radar-chart__dot {
  fill: var(--sky-deep);
  stroke: #fffdf9;
  stroke-width: 2;
}

.home-radar-chart__label,
.home-radar-chart__value,
.home-radar-chart__scale {
  font-family: var(--font-sans);
  font-weight: 800;
  pointer-events: none;
}

.home-radar-chart__label {
  fill: var(--ink-soft);
  font-size: 11px;
}

.home-radar-chart__value {
  fill: var(--seal-deep);
  font-size: 12px;
}

.home-radar-chart__scale {
  fill: rgba(108, 99, 89, 0.56);
  font-size: 10px;
}

.home-radar-list {
  display: grid;
  gap: 8px;
}

.home-radar-note {
  margin: 0;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.home-radar-list span {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.72);
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 700;
}

.home-radar-list strong {
  color: var(--seal-deep);
}

.home-ledger {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 14px;
  align-items: start;
}

.home-ledger__main,
.home-ledger__side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.home-support-grid {
  display: block;
}

.archive-panel {
  padding: 20px;
  background:
    radial-gradient(circle at top right, rgba(240, 213, 184, 0.12), transparent 26%),
    rgba(255, 251, 247, 0.82);
  box-shadow: 0 12px 24px rgba(91, 67, 51, 0.045);
}

.home-list {
  display: grid;
  gap: 10px;
}

.home-list--scroll {
  max-height: 280px;
  overflow: auto;
}

.home-list--empty {
  color: var(--ink-faint);
}

.home-task-switch {
  display: inline-flex;
  padding: 4px;
  border-radius: 999px;
  background: rgba(76, 118, 106, 0.08);
  gap: 4px;
}

.home-task-switch__item {
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.home-task-switch__item.active {
  background: rgba(255, 255, 255, 0.9);
  color: var(--ink);
}

.home-task-actions {
  margin-top: 12px;
}

.home-list__item {
  padding: 14px 16px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: var(--radius-lg);
  background: rgba(255, 251, 247, 0.72);
}

.home-list__item--soft {
  background: rgba(248, 245, 240, 0.78);
}

.home-list__item p {
  color: var(--ink-faint);
  font-size: 12px;
}

.home-list__item strong {
  display: block;
  margin-top: 6px;
  color: var(--ink);
  font-size: 15px;
  line-height: 1.55;
}

.home-list__item p {
  margin-top: 5px;
  line-height: 1.68;
}

.life-tree-panel {
  overflow: hidden;
  border-color: rgba(143, 184, 198, 0.3);
  background:
    radial-gradient(circle at 84% 8%, rgba(215, 104, 72, 0.09), transparent 26%),
    linear-gradient(180deg, rgba(232, 240, 244, 0.64), rgba(255, 253, 250, 0.78));
}

.life-tree-panel--solo {
  background:
    radial-gradient(circle at top right, rgba(240, 213, 184, 0.18), transparent 24%),
    linear-gradient(180deg, rgba(255, 250, 244, 0.92), rgba(255, 253, 250, 0.84));
}

.tree-score {
  min-width: 54px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(67, 98, 115, 0.22);
  border-radius: var(--radius-sm);
  color: var(--sky-deep);
  background: rgba(255, 253, 250, 0.72);
  font-weight: 800;
}

.tree-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}

.tree-progress-head strong {
  color: var(--sky-deep);
  font-size: 13px;
}

.tree-progress {
  position: relative;
  height: 8px;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: rgba(44, 48, 39, 0.08);
}

.tree-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--sky-deep), var(--seal));
  transition: width 260ms ease;
}

.tree-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tree-water-btn:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.tree-leaves {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0;
}

.tree-leaves--solo {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tree-leaf {
  padding: 9px 8px;
  border: 1px solid rgba(44, 48, 39, 0.1);
  border-radius: var(--radius-sm);
  background: rgba(255, 253, 250, 0.64);
}

.tree-leaf span {
  color: var(--ink-faint);
  font-size: 11px;
  font-weight: 800;
}

.tree-leaf strong {
  display: block;
  margin-top: 2px;
  color: var(--seal-deep);
  font-size: 15px;
}

@keyframes treeSeed {
  0%, 10% { transform: scale(0.75); opacity: 1; }
  22%, 100% { transform: scale(0.2) translateY(18px); opacity: 0; }
}

@keyframes treeSprout {
  0%, 16% { stroke-dashoffset: 160; opacity: 0; }
  26%, 42% { stroke-dashoffset: 0; opacity: 1; }
  58%, 100% { opacity: 0; }
}

@keyframes treeGrow {
  0%, 38% { transform: scale(0.18); opacity: 0; }
  54% { transform: scale(0.74); opacity: 1; }
  72%, 100% { transform: scale(1); opacity: 1; }
}

@keyframes treeBranch {
  0%, 48% { stroke-dashoffset: 130; opacity: 0; }
  66%, 100% { stroke-dashoffset: 0; opacity: 1; }
}

@keyframes treeLeafBloom {
  0%, 56% { transform: scale(0.05); opacity: 0; }
  72% { transform: scale(1.08); opacity: 0.95; }
  86%, 100% { transform: scale(1); opacity: 1; }
}

@keyframes treeSoilPulse {
  0%, 100% { transform: scaleX(0.88); opacity: 0.62; }
  50% { transform: scaleX(1); opacity: 1; }
}

@keyframes energyGlowPulse {
  0%, 100% {
    opacity: 0.94;
    box-shadow:
      0 8px 16px rgba(194, 116, 50, 0.16),
      inset 0 0 9px rgba(255, 255, 255, 0.58);
  }
  50% {
    opacity: 1;
    box-shadow:
      0 10px 20px rgba(194, 116, 50, 0.2),
      inset 0 0 11px rgba(255, 255, 255, 0.66),
      0 0 0 4px rgba(244, 187, 80, 0.08);
  }
}

@keyframes energyCollectPulse {
  0% { transform: scale(1); }
  45% { transform: scale(1.12); }
  100% { transform: scale(0.96); }
}

@keyframes energyGainFloat {
  0% { opacity: 0; transform: translate(-50%, 10px) scale(0.86); }
  18% { opacity: 1; }
  100% { opacity: 0; transform: translate(-50%, -22px) scale(1.1); }
}

@keyframes energyDropPulse {
  0%, 100% { transform: scale(0.88); opacity: 0.7; }
  50% { transform: scale(1.18); opacity: 1; }
}

@media (max-width: 940px) {
  .home-dossier,
  .home-ledger,
  .home-analytics-strip {
    grid-template-columns: 1fr;
  }

  .dossier-copy { min-height: auto; }
  .dossier-ledger { grid-template-columns: 1fr; }
  .home-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

@media (max-width: 600px) {
  .home-page {
    width: min(100% - 16px, var(--content-max));
    padding-top: 18px;
  }

  .home-dossier {
    padding: 18px;
    row-gap: 14px;
  }

  .dossier-stamp,
  .hero-subactions {
    display: none;
  }

  .dossier-copy h2 {
    max-width: calc(100% - 160px);
    margin-right: 160px;
    font-size: 22px;
  }

  .tree-leaves {
    grid-template-columns: 1fr;
  }

  .tree-leaves--solo {
    grid-template-columns: 1fr;
  }

  .dossier-ledger,
  .home-radar-layout {
    grid-template-columns: 1fr;
  }

  .dossier-ledger {
    display: block;
    gap: 0;
  }

  .relationship-switcher {
    position: absolute;
    top: 42px;
    right: 18px;
    grid-template-columns: auto minmax(84px, 1fr);
    width: 158px;
    padding: 7px 8px;
    white-space: nowrap;
  }

  .relationship-switcher span {
    font-size: 9.5px;
  }

  .relationship-switcher select {
    min-height: 30px;
    padding-left: 6px;
    padding-right: 18px;
    font-size: 11.5px;
  }

  .home-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
  }

  .metric-item {
    min-height: 60px;
    padding: 9px 3px 7px;
    border-radius: 12px;
  }

  .metric-item::before {
    left: 8px;
    width: 18px;
  }

  .metric-item span {
    gap: 3px !important;
    font-size: 10px;
  }

  .metric-item span svg {
    width: 12px;
    height: 12px;
    flex: 0 0 12px;
  }

  .metric-item strong {
    margin-top: 5px;
    font-size: 13px;
  }

  .archive-panel { padding: 16px; }
}

@media (max-width: 340px) {
  .home-page {
    width: min(100% - 12px, var(--content-max));
  }

  .home-dossier {
    padding: 14px;
  }

  .relationship-switcher {
    top: 36px;
    right: 14px;
    width: 150px;
  }

  .dossier-copy h2 {
    max-width: calc(100% - 152px);
    margin-right: 152px;
    font-size: 20px;
  }

  .home-metrics {
    gap: 3px;
  }

  .metric-item {
    min-height: 58px;
    padding-inline: 2px;
  }

  .metric-item span {
    font-size: 9px;
  }

  .metric-item strong {
    font-size: 12px;
  }
}

.home-daily-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 12px;
  padding: 8px 12px;
  background: rgba(189, 75, 53, 0.05);
  border-radius: 10px;
  border-left: 3px solid var(--seal, #bd4b35);
}

.home-daily-note__text {
  font-size: 13px;
  color: var(--ink-soft, #594f48);
  line-height: 1.5;
  flex: 1;
  word-break: break-all;
}

.btn-note-rotate {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  color: var(--ink-muted, #8a7c73);
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(112, 72, 46, 0.15);
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.btn-note-rotate:hover {
  color: var(--seal, #bd4b35);
  border-color: var(--seal, #bd4b35);
  background: #fff;
}
</style>

<template>
  <div class="challenges-page page-shell page-shell--wide page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">{{ hasPairContext ? '日常安排' : '个人安排' }}</p>
        <h2>{{ hasPairContext ? '今天 / 明天安排' : '今天先做这些' }}</h2>
      </div>
      <div class="hero-actions challenge-head-actions">
        <div v-if="hasPairContext" class="scope-switch" role="group" aria-label="安排日期切换">
          <button
            class="scope-switch__item"
            :class="{ active: scopeTab === 'today' }"
              :aria-pressed="scopeTab === 'today'"
            type="button"
            @click="setScope('today')"
          >
            今天
          </button>
          <button
            class="scope-switch__item"
            :class="{ active: scopeTab === 'tomorrow' }"
              :aria-pressed="scopeTab === 'tomorrow'"
            type="button"
            @click="setScope('tomorrow')"
          >
            明天
          </button>
        </div>
        <button
          v-if="hasPairContext"
          class="btn btn-ghost btn-sm"
          type="button"
          @click="toggleSettingsPanel"
        >
          {{ showSettingsPanel ? '收起设置' : '安排设置' }}
        </button>
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          :disabled="!canCreateTask"
          @click="openComposer()"
        >
          新增安排
        </button>
      </div>
    </div>

    <div v-if="!hasPairContext && !userStore.isDemoMode" class="card">
      <p class="eyebrow">还没有双人安排</p>
      <h3>先建立关系，再安排两个人一起做的事</h3>
      <div class="hero-actions">
        <button class="btn btn-primary btn-sm" type="button" @click="$router.push('/pair')">去关系页</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/checkin')">先去记录</button>
      </div>
    </div>

    <template v-else>
      <div class="challenge-shell">
        <div class="card card-accent challenge-summary-card">
          <div class="challenge-summary-card__head">
            <div>
              <p class="eyebrow">{{ scopeTab === 'today' ? '今天进度' : '明天安排' }}</p>
              <h3>{{ summaryTitle }}</h3>
            </div>
            <span class="pill pill--soft">{{ scopeTab === 'today' ? '当天执行' : '提前预排' }}</span>
          </div>
          <div v-if="displayDailyNote" class="challenge-daily-note">
            <span class="challenge-daily-note__text">“{{ displayDailyNote }}”</span>
            <button
              class="btn-note-rotate"
              type="button"
              title="换一句每日寄语"
              @click="rotateDailyNote"
            >
              <RotateCcw :size="12" />
              <span>换一句</span>
            </button>
          </div>
          <div v-if="scopeTab === 'today'" class="progress-track challenge-progress">
            <span class="progress-track__fill" :style="{ width: `${progressPercent}%` }"></span>
          </div>
        </div>

        <div v-if="showSettingsPanel && hasPairContext" class="card challenge-settings-card">
          <div class="card-header card-header--stack">
            <div>
              <p class="eyebrow">这段关系的安排设置</p>
              <h3>单独调整这一段关系</h3>
            </div>
            <div class="hero-actions">
              <button class="btn btn-ghost btn-sm" type="button" :disabled="savingSettings" @click="resetPairSettings">
                跟随全局
              </button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="savingSettings" @click="savePairSettings">
                {{ savingSettings ? '保存中...' : '保存设置' }}
              </button>
            </div>
          </div>

          <div class="challenge-settings-grid">
            <label class="field">
              <span>每天安排条数</span>
              <input v-model.number="settingsDraft.daily_ai_task_count" class="input" type="number" min="3" max="8" />
            </label>
            <label class="field">
              <span>明天安排提醒</span>
              <select v-model="settingsDraft.reminder_enabled" class="input">
                <option :value="true">开启</option>
                <option :value="false">关闭</option>
              </select>
            </label>
            <label class="field">
              <span>提醒时间</span>
              <input v-model="settingsDraft.reminder_time" class="input" type="time" />
            </label>
          </div>
        </div>

        <div v-if="showComposer" class="card challenge-composer-card">
          <div class="card-header card-header--stack">
            <div>
              <p class="eyebrow">{{ editingTaskId ? '编辑手动安排' : '新增手动安排' }}</p>
              <h3>{{ scopeTab === 'tomorrow' ? '加到明天安排里' : '加到今天安排里' }}</h3>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="closeComposer">取消</button>
          </div>

          <div class="challenge-composer-grid">
            <label class="field">
              <span>安排标题</span>
              <input v-model="taskDraft.title" class="input" type="text" maxlength="100" placeholder="比如：先留出 10 分钟" />
            </label>
            <label class="field">
              <span>安排分类</span>
              <select v-model="taskDraft.category" class="input">
                <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>
            <label class="field">
              <span>给谁做</span>
              <select v-model="taskDraft.target_scope" class="input">
                <option value="self">只给自己</option>
                <option v-if="hasPairContext" value="both">双方一起</option>
              </select>
            </label>
            <label class="field">
              <span>重要度</span>
              <select v-model="taskDraft.importance_level" class="input">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </label>
            <label class="field field--full">
              <span>具体做点啥</span>
              <textarea v-model="taskDraft.description" class="input input-textarea" rows="3" maxlength="400" placeholder="简单写写这件小事怎么做，比如：'散步时牵着手走10分钟'、'睡前互道一句晚安'~"></textarea>
            </label>
          </div>

          <div class="hero-actions">
            <button class="btn btn-primary btn-sm" type="button" :disabled="savingTask || !taskDraft.title.trim()" @click="saveTask">
              {{ savingTask ? '保存中...' : (editingTaskId ? '保存修改' : '保存安排') }}
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-header card-header--stack">
            <div>
              <p class="eyebrow">{{ scopeTab === 'today' ? '今天安排' : '明天安排' }}</p>
              <h3>{{ scopeTab === 'today' ? '今天要做的事' : '明天想做的事' }}</h3>
            </div>
            <div class="hero-actions">
              <button class="btn btn-secondary btn-sm" type="button" :disabled="loadingTasks || Boolean(scheduleError)" @click="openScheduleAgent()">{{ scopeTab === 'today' ? '让 AI 帮我选一件' : '和 AI 商量明天' }}</button>
              <button class="btn btn-ghost btn-sm" type="button" :disabled="loadingTasks" @click="loadCurrentTasks">
                {{ loadingTasks ? '加载中…' : '刷新' }}
              </button>
              <button class="btn btn-secondary btn-sm" type="button" @click="toggleOrderAdjust">
                {{ isAdjustingOrder ? '取消' : '调整' }}
              </button>
            </div>
          </div>

          <div v-if="loadingTasks" class="empty-state">正在加载安排…</div>
          <div v-else-if="scheduleError" class="empty-state" role="alert">{{ scheduleError }}</div>
          <TransitionGroup v-else-if="taskItems.length" name="task-row" tag="div" class="task-stack">
            <article
              v-for="(task, index) in taskItems"
              :key="task.id"
              :data-task-row="task.id"
              :data-task-completed="isCompletedTask(task) ? 'true' : 'false'"
              class="task-card"
              :class="{
                'task-card--child': Boolean(task.parent_task_id),
                'task-card--done': isCompletedTask(task),
                'task-card--dragging': draggingTaskId === task.id,
                'task-card--adjusting': isAdjustingOrder,
                'task-card--expanded': expandedTaskId === task.id && !isAdjustingOrder,
              }"
              @click="toggleTaskDetail(task)"
            >
              <span
                v-if="canDragTask(task)"
                class="task-card__handle"
                aria-hidden="true"
                @pointerdown.stop.prevent="startOrderPointer(task, $event)"
              >≡</span>
              <div class="task-card__main">
                <div class="task-card__head">
                  <div class="task-card__title-wrap">
                    <span class="task-card__order">{{ index + 1 }}</span>
                    <strong>{{ task.title }}</strong>
                  </div>
                  <button v-if="scopeTab === 'today' && task.status !== 'cancelled'" class="btn btn-ghost btn-sm" type="button" :aria-label="`${task.title}：更新结果`" @click.stop="resultTask = task">{{ taskStatusLabel(task) }} · 更新</button>
                  <span v-else class="task-card__status">{{ scopeTab === 'tomorrow' ? '待开始' : taskStatusLabel(task) }}</span>
                </div>
                <div class="task-card__meta">
                  <span class="pill pill--soft">{{ task.source === 'manual' ? '手动' : '自动' }}</span>
                  <span class="pill pill--soft">{{ importanceLabel(task.importance_level) }}</span>
                  <span class="pill pill--soft">{{ task.target_scope === 'both' ? '双方' : '自己' }}</span>
                </div>
                <div v-if="expandedTaskId === task.id && !isAdjustingOrder" class="task-card__detail">
                  <p v-if="task.description">{{ task.description }}</p>
                  <p v-if="task.feedback" class="task-feedback-saved">后来：{{ describeTaskFeedback(task.feedback) }}</p>
                  <div class="task-card__detail-actions" @click.stop>
                    <button v-if="!isCompletedTask(task)" class="btn btn-ghost btn-sm" type="button" @click="openScheduleAgent(task)">请 AI 拆成小步</button>
                    <button
                      v-if="task.refreshable && hasPairContext && !isCompletedTask(task)"
                      class="btn btn-ghost btn-sm"
                      type="button"
                      :disabled="refreshingTaskId === task.id"
                      @click="refreshSingleTask(task)"
                    >
                      {{ refreshingTaskId === task.id ? '更换中...' : '换一条' }}
                    </button>
                    <button
                      v-if="task.editable && !isCompletedTask(task)"
                      class="btn btn-ghost btn-sm"
                      type="button"
                      @click="openComposer(task)"
                    >
                      编辑
                    </button>
                    <button
                      v-if="scopeTab === 'today' && task.status !== 'cancelled'"
                      class="btn btn-secondary btn-sm"
                      type="button"
                      @click="openFeedback(task.id)"
                    >
                      {{ task.feedback ? '更新反馈' : '后来怎么样' }}
                    </button>
                    <button
                      v-if="scopeTab === 'today' && !isCompletedTask(task)"
                      class="btn btn-secondary btn-sm"
                      type="button"
                      :disabled="completingTaskId === task.id"
                      @click="completeTask(task)"
                    >
                      {{ completingTaskId === task.id ? '保存中...' : '完成' }}
                    </button>
                    <button v-if="task.feedback" class="btn btn-ghost btn-sm" type="button" @click="openTaskFollowup(task)">想想明天</button>
                  </div>
                </div>
              </div>

              <div v-if="activeFeedbackTaskId === task.id" class="task-feedback-panel" @click.stop>
                <strong>后来怎么样？</strong>
                <div class="task-feedback-choices" role="group" aria-label="这件事的结果">
                  <button v-for="option in feedbackOptionsFor(task)" :key="option.value" type="button" class="btn btn-sm" :class="feedbackDraftFor(task.id).outcome === option.value ? 'btn-secondary' : 'btn-ghost'" :aria-pressed="feedbackDraftFor(task.id).outcome === option.value" @click="feedbackDraftFor(task.id).outcome = option.value">{{ option.label }}</button>
                </div>
                <label class="field"><span>补充一句（选填）</span><textarea v-model="feedbackDraftFor(task.id).note" class="input input-textarea" rows="2" maxlength="200" placeholder="比如：今天太忙，还没找到合适的时间。"></textarea></label>
                <details v-if="isCompletedTask(task)" class="task-feedback-ratings">
                  <summary>再具体一点（选填）</summary>
                  <div class="task-feedback-panel__grid">
                  <label class="field">
                    <span>有用吗</span>
                    <select v-model.number="feedbackDraftFor(task.id).usefulness_score" class="input">
                      <option :value="null">请选择</option>
                      <option v-for="option in usefulnessOptions" :key="`use-${option.value}`" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>费劲吗</span>
                    <select v-model.number="feedbackDraftFor(task.id).friction_score" class="input">
                      <option :value="null">请选择</option>
                      <option v-for="option in frictionOptions" :key="`fri-${option.value}`" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>关系变化</span>
                    <select v-model.number="feedbackDraftFor(task.id).relationship_shift_score" class="input">
                      <option :value="null">请选择</option>
                      <option v-for="option in relationshipShiftOptions" :key="`shift-${option.value}`" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  </div>
                </details>
                <div class="hero-actions">
                  <button class="btn btn-primary btn-sm" type="button" :disabled="submittingFeedbackId === task.id || !isFeedbackReady(task.id)" @click="submitFeedback(task.id)">
                    {{ submittingFeedbackId === task.id ? '保存中...' : '记下结果' }}
                  </button>
                  <button class="btn btn-ghost btn-sm" type="button" @click="closeFeedback">先跳过</button>
                </div>
              </div>
            </article>
            <div v-if="isAdjustingOrder" key="order-confirm" class="task-order-confirm">
              <span>按住右侧拖动排序</span>
              <button class="btn btn-primary btn-sm" type="button" @click="confirmTaskOrder">确定</button>
            </div>
          </TransitionGroup>
          <div v-else class="empty-state">{{ scopeTab === 'today' ? '今天还没有安排' : '明天还没有安排' }}</div>
        </div>
      </div>
    </template>
    <TaskResultDialog v-if="resultTask" :task="resultTask" :pair-id="pair?.id" :date="activeDate" @close="resultTask = null" @saved="loadCurrentTasks" @analyze="scheduleContext = $event" />
    <ContextAgentDialog v-if="scheduleContext" :context="scheduleContext" @close="scheduleContext = null" />
  </div>
</template>

<script setup>
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import TaskResultDialog from '@/components/TaskResultDialog.vue'
import { buildDemoSchedule, buildScheduleContext, buildTaskFollowupContext, describeTaskFeedback, feedbackOutcomes, feedbackPayload, createLatestRequest, scheduleDate, demoScheduleCache } from '@/utils/taskSchedule'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RotateCcw } from 'lucide-vue-next'
import { clampDailyNote, getNextDailyNote, DAILY_NOTE_CANDIDATES } from '@/utils/dailyNotes'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { useUserStore } from '@/stores/user'
import {
  completeSoloTaskEntry,
  createSoloTaskEntry,
  loadSoloTaskPack,
  saveSoloTaskFeedbackEntry,
} from '@/utils/soloWorkspace'
import { createRefreshAttemptGuard, parseRetryAfterSeconds } from '@/utils/refreshGuards'

const DEFAULT_SETTINGS = {
  daily_ai_task_count: 5,
  reminder_enabled: true,
  reminder_time: '21:00',
  reminder_timezone: 'Asia/Shanghai',
}

const categoryOptions = [
  { value: 'communication', label: '沟通' },
  { value: 'repair', label: '缓和' },
  { value: 'connection', label: '连接' },
  { value: 'activity', label: '行动' },
  { value: 'reflection', label: '复盘' },
]

const usefulnessOptions = [
  { value: 1, label: '1 分 · 没用' },
  { value: 2, label: '2 分 · 偏弱' },
  { value: 3, label: '3 分 · 还行' },
  { value: 4, label: '4 分 · 挺有用' },
  { value: 5, label: '5 分 · 很有用' },
]

const frictionOptions = [
  { value: 1, label: '1 分 · 很轻' },
  { value: 2, label: '2 分 · 偏轻' },
  { value: 3, label: '3 分 · 一般' },
  { value: 4, label: '4 分 · 偏费劲' },
  { value: 5, label: '5 分 · 很费劲' },
]

const relationshipShiftOptions = [
  { value: -2, label: '1 分 · 更远了' },
  { value: -1, label: '2 分 · 有点疏' },
  { value: 0, label: '3 分 · 没变化' },
  { value: 1, label: '4 分 · 近了一点' },
  { value: 2, label: '5 分 · 明显更近' },
]

function normalizeScope(value) {
  return String(value || '').trim().toLowerCase() === 'tomorrow' ? 'tomorrow' : 'today'
}

function isoDate(offset = 0) {
  const now = new Date()
  const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
  const pad = (value) => String(value).padStart(2, '0')
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`
}

function createTaskDraft(scope = 'today') {
  return {
    title: '',
    description: '',
    category: 'activity',
    target_scope: 'self',
    importance_level: 'medium',
    due_date: scope === 'tomorrow' ? isoDate(1) : isoDate(0),
  }
}

function createFeedbackDraft(saved = {}) {
  return {
    outcome: null,
    usefulness_score: null,
    friction_score: null,
    relationship_shift_score: null,
    note: '',
    ...saved,
  }
}

function buildDemoTaskPayload(scope = 'today') {
  const saved = demoScheduleCache.read({ owner: userStore.me?.id || 'sample', pairId: pair.value?.id, date: scheduleDate(scope) })
  if (saved) return saved
  return { ...buildDemoSchedule(demoFixture.tasks, scope), effective_settings: { ...DEFAULT_SETTINGS } }
}

function buildDemoPairSettings() {
  return {
    pair_id: demoFixture.currentPairId,
    overrides: {},
    effective_settings: { ...DEFAULT_SETTINGS },
  }
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})

const scopeTab = ref(normalizeScope(route.query.scope))
const tasksPayload = ref({ tasks: [] })
const pairSettingsPayload = ref(buildDemoPairSettings())
const settingsDraft = ref({ ...DEFAULT_SETTINGS })
const loadingTasks = ref(false)
const savingSettings = ref(false)
const showSettingsPanel = ref(false)
const showComposer = ref(false)
const editingTaskId = ref('')
const taskDraft = ref(createTaskDraft(scopeTab.value))
const savingTask = ref(false)
const savingTaskId = ref('')
const refreshingTaskId = ref('')
const singleTaskRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })
const completingTaskId = ref('')
const activeFeedbackTaskId = ref('')
const feedbackDrafts = ref({})
const submittingFeedbackId = ref('')
const soloPayload = ref({ tasks: [] })
const draggingTaskId = ref('')
const isAdjustingOrder = ref(false)
const expandedTaskId = ref('')
const orderDragState = ref(null)

const pair = computed(() => userStore.activePair)
const hasPairContext = computed(() => Boolean(pair.value?.id) || userStore.isDemoMode)
const activeDate = computed(() => (scopeTab.value === 'tomorrow' ? isoDate(1) : isoDate(0)))
const taskItems = computed(() => {
  const tasks = [...(tasksPayload.value.tasks || [])]
  return tasks.sort((a, b) => Number(isCompletedTask(a)) - Number(isCompletedTask(b)))
})
const completedCount = computed(() => taskItems.value.filter((task) => task.status === 'completed').length)
const progressPercent = computed(() => taskItems.value.length ? Math.round((completedCount.value / taskItems.value.length) * 100) : 0)
const summaryTitle = computed(() => {
  if (scopeTab.value === 'today') return `已完成 ${completedCount.value}/${taskItems.value.length || 0} 条`
  return `已排好 ${taskItems.value.length || 0} 条明天安排`
})
const canCreateTask = computed(() => {
  if (!hasPairContext.value) return true
  return !tasksPayload.value.manual_task_limit_reached
})

const customDailyNote = ref('')
const displayDailyNote = computed(() => {
  if (customDailyNote.value) {
    return clampDailyNote(customDailyNote.value)
  }
  const sourceNote = scopeTab.value === 'tomorrow'
    ? (tasksPayload.value.planning_note || tasksPayload.value.daily_note)
    : tasksPayload.value.daily_note
  return clampDailyNote(sourceNote || DAILY_NOTE_CANDIDATES[0])
})

function rotateDailyNote() {
  const next = getNextDailyNote(displayDailyNote.value)
  customDailyNote.value = next
}

watch(
  () => route.query.scope,
  (value) => {
    scopeTab.value = normalizeScope(value)
    customDailyNote.value = ''
  }
)

watch(
  () => route.query.panel,
  (value) => {
    showSettingsPanel.value = String(value || '').trim() === 'settings'
    if (showSettingsPanel.value) loadPairSettings()
  },
  { immediate: true }
)

watch(
  () => route.query.pair_id,
  async (value) => {
    const pairId = String(value || '').trim()
    if (!pairId || pairId === userStore.activePairId) return
    await userStore.switchPair(pairId)
  },
  { immediate: true }
)

watch(
  () => pair.value?.id,
  (value) => {
    if (value && String(route.query.pair_id || '') !== String(value)) {
      router.replace({ query: { ...route.query, pair_id: value, scope: scopeTab.value, date: activeDate.value } })
    }
  },
  { immediate: true }
)

watch(
  [() => pair.value?.id, scopeTab],
  () => {
    if (hasPairContext.value) {
      loadCurrentTasks()
      if (showSettingsPanel.value) loadPairSettings()
    }
  }
)

onMounted(() => {
  if (hasPairContext.value) {
    loadCurrentTasks()
  } else {
    soloPayload.value = loadSoloTaskPack()
    tasksPayload.value = { tasks: soloPayload.value.tasks || [] }
  }
})

onBeforeUnmount(() => {
  removeOrderPointerListeners()
})

function setScope(scope) {
  const normalized = normalizeScope(scope)
  isAdjustingOrder.value = false
  expandedTaskId.value = ''
  clearTaskDrag()
  scopeTab.value = normalized
  router.replace({
    query: {
      ...route.query,
      scope: normalized,
      date: normalized === 'tomorrow' ? isoDate(1) : isoDate(0),
      pair_id: pair.value?.id || route.query.pair_id,
    },
  })
}

function toggleSettingsPanel() {
  showSettingsPanel.value = !showSettingsPanel.value
  if (showSettingsPanel.value) loadPairSettings()
}

async function loadCurrentTasks() {
  const current = scheduleRequests.begin()
  const requestScope = scopeTab.value
  const requestPair = pair.value?.id
  loadingTasks.value = false
  scheduleError.value = ''
  tasksPayload.value = { tasks: [] }
  if (!hasPairContext.value) {
    soloPayload.value = loadSoloTaskPack({ isoDate: scheduleDate(scopeTab.value) })
    tasksPayload.value = { tasks: soloPayload.value.tasks || [] }
    return
  }
  if (!(hasPairContext.value)) return
  if (userStore.isDemoMode) {
    tasksPayload.value = buildDemoTaskPayload(requestScope)
    return
  }
  loadingTasks.value = true
  try {
    const result = await api.getDailyTasks(requestPair, { forDate: scheduleDate(requestScope), dateScope: requestScope })
    if (current()) tasksPayload.value = result
  } catch (error) {
    if (current()) scheduleError.value = error.message || '安排没加载出来，请重试'
  } finally {
    if (current()) loadingTasks.value = false
  }
}

async function loadPairSettings() {
  if (!hasPairContext.value) return
  if (userStore.isDemoMode) {
    pairSettingsPayload.value = buildDemoPairSettings()
    settingsDraft.value = { ...pairSettingsPayload.value.effective_settings }
    return
  }
  if (!pair.value?.id) return
  try {
    pairSettingsPayload.value = await api.getPairTaskSettings(pair.value.id)
    settingsDraft.value = {
      ...DEFAULT_SETTINGS,
      ...(pairSettingsPayload.value.effective_settings || {}),
    }
  } catch (error) {
    showToast(error.message || '安排设置没加载出来')
  }
}

async function savePairSettings() {
  if (userStore.isDemoMode) {
    pairSettingsPayload.value = {
      ...buildDemoPairSettings(),
      effective_settings: { ...settingsDraft.value },
    }
    showToast('这段关系的安排设置已保存')
    await loadCurrentTasks()
    return
  }
  if (!pair.value?.id) return
  savingSettings.value = true
  try {
    pairSettingsPayload.value = await api.updatePairTaskSettings(pair.value.id, {
      daily_ai_task_count: Number(settingsDraft.value.daily_ai_task_count || 5),
      reminder_enabled: Boolean(settingsDraft.value.reminder_enabled),
      reminder_time: settingsDraft.value.reminder_time || '21:00',
    })
    settingsDraft.value = {
      ...DEFAULT_SETTINGS,
      ...(pairSettingsPayload.value.effective_settings || {}),
    }
    showToast('这段关系的安排设置已保存')
    await loadCurrentTasks()
  } catch (error) {
    showToast(error.message || '安排设置没保存上')
  } finally {
    savingSettings.value = false
  }
}

async function resetPairSettings() {
  if (userStore.isDemoMode) {
    settingsDraft.value = { ...DEFAULT_SETTINGS }
    pairSettingsPayload.value = buildDemoPairSettings()
    showToast('已经恢复跟随全局设置')
    await loadCurrentTasks()
    return
  }
  if (!pair.value?.id) return
  savingSettings.value = true
  try {
    pairSettingsPayload.value = await api.updatePairTaskSettings(pair.value.id, {
      daily_ai_task_count: null,
      reminder_enabled: null,
      reminder_time: null,
      reminder_timezone: null,
    })
    settingsDraft.value = {
      ...DEFAULT_SETTINGS,
      ...(pairSettingsPayload.value.effective_settings || {}),
    }
    showToast('已经恢复跟随全局设置')
    await loadCurrentTasks()
  } catch (error) {
    showToast(error.message || '这次没恢复默认，请稍后再试')
  } finally {
    savingSettings.value = false
  }
}

function openComposer(task = null) {
  if (task) {
    editingTaskId.value = task.id
    taskDraft.value = {
      title: task.title || '',
      description: task.description || '',
      category: task.category || 'activity',
      target_scope: task.target_scope || 'self',
      importance_level: task.importance_level || 'medium',
      due_date: task.due_date || activeDate.value,
    }
  } else {
    editingTaskId.value = ''
    taskDraft.value = createTaskDraft(scopeTab.value)
  }
  showComposer.value = true
}

function closeComposer() {
  showComposer.value = false
  editingTaskId.value = ''
  taskDraft.value = createTaskDraft(scopeTab.value)
}

async function saveTask() {
  const payload = {
    ...taskDraft.value,
    title: taskDraft.value.title.trim(),
    description: String(taskDraft.value.description || '').trim(),
    due_date: activeDate.value,
  }
  if (!payload.title) {
    showToast('先写一个安排标题')
    return
  }

  savingTask.value = true
  try {
    if (!hasPairContext.value) {
      if (editingTaskId.value) {
        showToast('个人模式暂不支持编辑旧安排，请重新新增一条')
      } else {
        createSoloTaskEntry(payload)
      }
      soloPayload.value = loadSoloTaskPack()
      tasksPayload.value = { tasks: soloPayload.value.tasks || [] }
    } else if (userStore.isDemoMode) {
      showToast(editingTaskId.value ? '样例安排已更新' : '样例安排已新增')
      const task = { ...payload, id: editingTaskId.value || `sample-manual-${Date.now()}`, source: 'manual', status: 'pending', editable: true, importance_adjustable: true, refreshable: false }
      const items = editingTaskId.value ? taskItems.value.map(item => item.id === editingTaskId.value ? { ...item, ...task } : item) : [...taskItems.value, task]
      tasksPayload.value = { ...tasksPayload.value, tasks: items, manual_task_count: items.filter(item => item.source === 'manual').length }
    } else if (editingTaskId.value) {
      await api.updateTask(editingTaskId.value, payload)
      await loadCurrentTasks()
    } else {
      await api.createManualTask(pair.value.id, payload)
      await loadCurrentTasks()
    }
    closeComposer()
  } catch (error) {
    showToast(error.message || '安排没保存上')
  } finally {
    savingTask.value = false
  }
}

function nextImportance(value, direction) {
  const levels = ['low', 'medium', 'high']
  const currentIndex = levels.indexOf(String(value || 'medium'))
  const safeIndex = currentIndex >= 0 ? currentIndex : 1
  const targetIndex = Math.min(levels.length - 1, Math.max(0, safeIndex + direction))
  return levels[targetIndex]
}

function commitTaskOrder(tasks) {
  tasksPayload.value = {
    ...tasksPayload.value,
    tasks,
  }
}

function toggleOrderAdjust() {
  isAdjustingOrder.value = !isAdjustingOrder.value
  expandedTaskId.value = ''
  clearTaskDrag()
}

function confirmTaskOrder() {
  isAdjustingOrder.value = false
  clearTaskDrag()
  showToast('已确定')
}

function isCompletedTask(task) {
  return String(task?.status || '').toLowerCase() === 'completed'
}

function canDragTask(task) {
  return isAdjustingOrder.value
    && !isCompletedTask(task)
    && taskItems.value.filter((item) => !isCompletedTask(item)).length > 1
}

function toggleTaskDetail(task) {
  if (isAdjustingOrder.value) return
  expandedTaskId.value = expandedTaskId.value === task.id ? '' : task.id
  if (expandedTaskId.value !== task.id && activeFeedbackTaskId.value === task.id) {
    closeFeedback()
  }
}

function moveTask(task, direction) {
  const tasks = [...taskItems.value]
  const currentIndex = tasks.findIndex((item) => item.id === task.id)
  const targetIndex = currentIndex + direction
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= tasks.length) return
  const [moved] = tasks.splice(currentIndex, 1)
  tasks.splice(targetIndex, 0, moved)
  commitTaskOrder(tasks)
}

function startTaskDrag(task) {
  if (!isAdjustingOrder.value) return
  draggingTaskId.value = task.id
}

function clearTaskDrag() {
  draggingTaskId.value = ''
}

function dropTask(targetTask) {
  if (!isAdjustingOrder.value) return
  if (!draggingTaskId.value || draggingTaskId.value === targetTask.id) {
    clearTaskDrag()
    return
  }
  const tasks = [...taskItems.value]
  const fromIndex = tasks.findIndex((item) => item.id === draggingTaskId.value)
  const toIndex = tasks.findIndex((item) => item.id === targetTask.id)
  if (fromIndex < 0 || toIndex < 0) {
    clearTaskDrag()
    return
  }
  const [moved] = tasks.splice(fromIndex, 1)
  tasks.splice(toIndex, 0, moved)
  commitTaskOrder(tasks)
  clearTaskDrag()
}

function startOrderPointer(task, event) {
  if (!canDragTask(task)) return
  draggingTaskId.value = task.id
  orderDragState.value = {
    id: task.id,
    pointerId: event.pointerId,
  }
  event.currentTarget?.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleOrderPointerMove, { passive: false })
  window.addEventListener('pointerup', finishOrderPointer, { once: true })
  window.addEventListener('pointercancel', finishOrderPointer, { once: true })
}

function removeOrderPointerListeners() {
  window.removeEventListener('pointermove', handleOrderPointerMove)
  window.removeEventListener('pointerup', finishOrderPointer)
  window.removeEventListener('pointercancel', finishOrderPointer)
}

function finishOrderPointer() {
  clearTaskDrag()
  orderDragState.value = null
  removeOrderPointerListeners()
}

function reorderTaskByPointer(targetId, clientY) {
  const dragId = orderDragState.value?.id
  if (!dragId || dragId === targetId) return
  const escapedId = window.CSS?.escape ? window.CSS.escape(targetId) : targetId
  const targetRow = document.querySelector(`[data-task-row="${escapedId}"]`)
  if (!targetRow || targetRow.dataset.taskCompleted === 'true') return
  const rect = targetRow.getBoundingClientRect()
  const insertAfter = clientY > rect.top + rect.height / 2
  const tasks = [...taskItems.value]
  const fromIndex = tasks.findIndex((item) => item.id === dragId)
  const targetIndex = tasks.findIndex((item) => item.id === targetId)
  if (fromIndex < 0 || targetIndex < 0) return
  const [moved] = tasks.splice(fromIndex, 1)
  let insertIndex = targetIndex + (insertAfter ? 1 : 0)
  if (fromIndex < insertIndex) insertIndex -= 1
  tasks.splice(insertIndex, 0, moved)
  commitTaskOrder(tasks)
}

function handleOrderPointerMove(event) {
  if (!orderDragState.value?.id) return
  event.preventDefault()
  const rows = Array.from(document.querySelectorAll('[data-task-row]'))
    .filter((row) => row.dataset.taskCompleted !== 'true')
  const targetRow = rows.find((row) => {
    const rect = row.getBoundingClientRect()
    return event.clientY >= rect.top && event.clientY <= rect.bottom
  })
  if (targetRow) {
    reorderTaskByPointer(targetRow.dataset.taskRow, event.clientY)
  }
}

async function shiftImportance(task, direction) {
  const nextValue = nextImportance(task.importance_level, direction)
  if (nextValue === task.importance_level) return
  if (userStore.isDemoMode) {
    tasksPayload.value = {
      ...tasksPayload.value,
      tasks: taskItems.value.map((item) => (item.id === task.id ? { ...item, importance_level: nextValue } : item)),
    }
    return
  }
  savingTaskId.value = task.id
  try {
    await api.updateTask(task.id, { importance_level: nextValue })
    await loadCurrentTasks()
  } catch (error) {
    showToast(error.message || '重要度没更新成功')
  } finally {
    savingTaskId.value = ''
  }
}

async function refreshSingleTask(task) {
  if (refreshingTaskId.value) return
  if (userStore.isDemoMode) {
    tasksPayload.value = {
      ...tasksPayload.value,
      tasks: taskItems.value.map((item) => (
        item.id === task.id
          ? { ...item, title: `${item.title}·换一条`, description: '已换成更贴近状态的安排。' }
          : item
      )),
    }
    showToast('这条安排已经换好了')
    return
  }
  const remainingSeconds = singleTaskRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`安排换得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  singleTaskRefreshGuard.markRun()
  refreshingTaskId.value = task.id
  try {
    await api.refreshTask(task.id)
    await loadCurrentTasks()
    showToast('这条安排已经换好了')
  } catch (error) {
    if (error?.statusCode === 429) {
      singleTaskRefreshGuard.setCooldown(parseRetryAfterSeconds(error.message))
    }
    showToast(error.message || '这条安排没换成功')
  } finally {
    refreshingTaskId.value = ''
  }
}

async function completeTask(task) {
  if (!hasPairContext.value) {
    completeSoloTaskEntry(task.id)
    soloPayload.value = loadSoloTaskPack()
    tasksPayload.value = { tasks: soloPayload.value.tasks || [] }
    return
  }
  if (userStore.isDemoMode) {
    tasksPayload.value = {
      ...tasksPayload.value,
      tasks: taskItems.value.map((item) => (
        item.id === task.id
          ? { ...item, status: 'completed', status_label: '已完成', needs_feedback: true }
          : item
      )),
    }
    openFeedback(task.id)
    return
  }
  completingTaskId.value = task.id
  try {
    await api.completeTask(task.id)
    await loadCurrentTasks()
    openFeedback(task.id)
  } catch (error) {
    showToast(error.message || '完成状态没更新成功')
  } finally {
    completingTaskId.value = ''
  }
}

function openFeedback(taskId) {
  activeFeedbackTaskId.value = taskId
  expandedTaskId.value = taskId
  if (!feedbackDrafts.value[taskId]) {
    feedbackDrafts.value = {
      ...feedbackDrafts.value,
      [taskId]: createFeedbackDraft(taskItems.value.find(item => item.id === taskId)?.feedback || {}),
    }
  }
  const task = taskItems.value.find(item => item.id === taskId)
  if (task && !feedbackOptionsFor(task).some(option => option.value === feedbackDrafts.value[taskId].outcome)) feedbackDrafts.value[taskId].outcome = null
}

function feedbackOptionsFor(task) {
  return feedbackOutcomes.filter(option => isCompletedTask(task) ? option.value !== 'not_yet' : ['not_yet', 'difficult'].includes(option.value))
}

function closeFeedback() {
  activeFeedbackTaskId.value = ''
}

function feedbackDraftFor(taskId) {
  if (!feedbackDrafts.value[taskId]) {
    feedbackDrafts.value = {
      ...feedbackDrafts.value,
      [taskId]: createFeedbackDraft(),
    }
  }
  return feedbackDrafts.value[taskId]
}

function isFeedbackReady(taskId) {
  const draft = feedbackDraftFor(taskId)
  const task = taskItems.value.find(item => item.id === taskId)
  if (!task || scopeTab.value !== 'today') return false
  return Boolean(feedbackPayload(draft)) && (isCompletedTask(task) ? draft.outcome !== 'not_yet' : ['not_yet', 'difficult'].includes(draft.outcome))
}

async function submitFeedback(taskId) {
  const draft = feedbackPayload(feedbackDraftFor(taskId))
  if (!isFeedbackReady(taskId) || submittingFeedbackId.value) return
  const feedbackScope = JSON.stringify([userStore.token, userStore.me?.id, pair.value?.id, activeDate.value])
  const stillCurrent = () => feedbackScope === JSON.stringify([userStore.token, userStore.me?.id, pair.value?.id, activeDate.value])

  submittingFeedbackId.value = taskId
  try {
    if (!hasPairContext.value) {
      saveSoloTaskFeedbackEntry(taskId, draft)
      soloPayload.value = loadSoloTaskPack()
      tasksPayload.value = { tasks: soloPayload.value.tasks || [] }
    } else if (userStore.isDemoMode) {
      tasksPayload.value = {
        ...tasksPayload.value,
        tasks: taskItems.value.map((task) => (
          task.id === taskId
            ? { ...task, feedback: { ...draft }, needs_feedback: false }
            : task
        )),
      }
    } else {
      await api.submitTaskFeedback(taskId, draft)
      if (!stillCurrent()) return
      await loadCurrentTasks()
    }
    if (!stillCurrent()) return
    showToast('已记下这次结果')
    closeFeedback()
  } catch (error) {
    if (stillCurrent()) showToast(error.message || '这次反馈没保存上')
  } finally {
    submittingFeedbackId.value = ''
  }
}

function importanceLabel(value) {
  const map = { low: '低优先', medium: '中优先', high: '高优先' }
  return map[String(value || 'medium')] || '中优先'
}

function taskStatusLabel(task) {
  const label = String(task?.status_label || '').trim()
  if (label && !['pending', 'completed', 'cancelled'].includes(label.toLowerCase())) return label
  const map = {
    pending: '未完成',
    completed: '已完成',
    cancelled: '已取消',
  }
  return map[String(task?.status || 'pending').toLowerCase()] || '未完成'
}

watch(tasksPayload, payload => {
  if (userStore.isDemoMode && payload.for_date === activeDate.value) {
    demoScheduleCache.save({ owner: userStore.me?.id || 'sample', pairId: pair.value?.id, date: activeDate.value }, payload)
  }
}, { deep: true, flush: 'sync' })
const scheduleContext = ref(null)
const resultTask = ref(null)
const scheduleRequests = createLatestRequest()
const scheduleError = ref('')
function openScheduleAgent(task = null) {
  scheduleContext.value = buildScheduleContext(task ? [task] : taskItems.value, {
    scope: scopeTab.value, date: scheduleDate(scopeTab.value), pairId: pair.value?.id || null,
    isDemoMode: userStore.isDemoMode, single: Boolean(task),
  })
}
function openTaskFollowup(task) {
  scheduleContext.value = buildTaskFollowupContext(task, { pairId: pair.value?.id || null, isDemoMode: userStore.isDemoMode })
}
watch(() => [userStore.token, userStore.me?.id, pair.value?.id, scopeTab.value], () => {
  scheduleRequests.invalidate()
  scheduleContext.value = null
  resultTask.value = null
  activeFeedbackTaskId.value = ''
  feedbackDrafts.value = {}
  tasksPayload.value = { tasks: [] }
  loadingTasks.value = false
}, { flush: 'sync' })
watch(() => [userStore.token, userStore.me?.id], () => loadCurrentTasks())
onBeforeUnmount(() => scheduleRequests.invalidate())

</script>

<style scoped>
.task-feedback-choices { display: flex; flex-wrap: wrap; gap: 8px; }
.task-feedback-ratings summary { cursor: pointer; color: var(--ink-soft); font-size: 13px; margin-bottom: 10px; }
.task-feedback-saved { color: var(--ink-soft); font-size: 14px; }
.challenge-head-actions {
  align-items: center;
  flex-wrap: wrap;
}

.scope-switch {
  display: inline-flex;
  padding: 4px;
  border-radius: 999px;
  background: rgba(76, 118, 106, 0.08);
  gap: 4px;
}

.scope-switch__item {
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
}

.scope-switch__item.active {
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 10px 24px rgba(76, 118, 106, 0.12);
}

.challenge-shell {
  display: grid;
  gap: 18px;
}

.challenge-summary-card__head,
.task-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.challenge-progress {
  margin-top: 14px;
}

.challenge-settings-grid,
.challenge-composer-grid,
.task-feedback-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.field--full {
  grid-column: 1 / -1;
}

.task-stack {
  display: grid;
  gap: 8px;
}

.task-row-move,
.task-row-enter-active,
.task-row-leave-active {
  transition: transform 0.22s ease, opacity 0.18s ease;
}

.task-row-enter-from,
.task-row-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.task-card {
  min-height: 54px;
  padding: 0 12px;
  border-radius: 14px;
  border: 1px solid rgba(76, 118, 106, 0.12);
  background: rgba(255, 255, 255, 0.88);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: center;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.task-card--child {
  margin-left: 12px;
  border-style: dashed;
}

.task-card--done {
  background: rgba(244, 246, 241, 0.96);
}

.task-card--dragging {
  opacity: 0.58;
  border-color: rgba(189, 75, 53, 0.36);
  box-shadow: 0 16px 28px rgba(112, 72, 46, 0.12);
}

.task-card--expanded {
  align-items: start;
  padding-top: 12px;
  padding-bottom: 12px;
}

.task-card--adjusting {
  grid-template-columns: minmax(0, 1fr) 34px;
  gap: 8px;
}

.task-card__handle {
  grid-column: 2;
  grid-row: 1;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: rgba(76, 118, 106, 0.08);
  color: var(--ink-faint);
  cursor: grab;
  font-weight: 900;
  user-select: none;
}

.task-card__handle:active {
  cursor: grabbing;
}

.task-card__main {
  grid-column: 1;
  min-width: 0;
}

.task-card__title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.task-card__order {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: rgba(189, 75, 53, 0.1);
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 900;
}

.task-card__status {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--ink-soft);
}

.task-card__title-wrap strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__meta {
  display: none;
}

.task-card__detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(76, 118, 106, 0.14);
}

.task-card__detail p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.65;
}

.task-card__detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.task-feedback-panel {
  grid-column: 1 / -1;
  padding-top: 6px;
  border-top: 1px dashed rgba(76, 118, 106, 0.18);
}

.task-order-confirm {
  position: sticky;
  bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(189, 75, 53, 0.14);
  border-radius: 16px;
  background: rgba(255, 252, 248, 0.96);
  box-shadow: 0 14px 30px rgba(112, 72, 46, 0.1);
  color: var(--ink-soft);
  font-size: 13px;
}

@media (max-width: 720px) {
  .challenge-head-actions {
    width: 100%;
  }

  .challenge-head-actions .btn {
    flex: 1;
  }

  .task-card--child {
    margin-left: 10px;
  }

  .task-card {
    min-height: 50px;
    padding: 0 10px;
  }

  .task-card--adjusting {
    grid-template-columns: minmax(0, 1fr) 32px;
  }

  .task-card__order {
    width: 22px;
    height: 22px;
  }

  .task-card__handle {
    width: 28px;
    height: 28px;
  }
}

.challenge-daily-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  margin-bottom: 6px;
  padding: 8px 12px;
  background: rgba(189, 75, 53, 0.05);
  border-radius: 10px;
  border-left: 3px solid var(--seal, #bd4b35);
}

.challenge-daily-note__text {
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

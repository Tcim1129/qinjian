<template>
  <div class="relationship-space-detail page-shell page-shell--wide page-stack" :class="themeClass">
    <section
      v-if="pair && (pendingRequest || latestRequestResult)"
      class="relationship-space-detail__status-strip"
      :class="{
        'relationship-space-detail__status-strip--break': isPendingBreakRequest,
        'relationship-space-detail__status-strip--split': pendingRequest && latestRequestResult && !isPendingBreakRequest,
      }"
    >
      <article
        v-if="pendingRequest"
        class="relationship-space-detail__status-card relationship-space-detail__status-card--pending"
        :class="{
          'relationship-space-detail__status-card--generic': !isPendingBreakRequest,
          'relationship-space-detail__status-card--break': isPendingBreakRequest,
          'relationship-space-detail__status-card--retaining': isPendingBreakRequest && pendingBreakPhase === 'retaining',
        }"
      >
        <template v-if="isPendingBreakRequest">
          <div class="relationship-space-detail__break-header">
            <div class="relationship-space-detail__break-header-copy">
              <p class="eyebrow">{{ pendingRequestEyebrow }}</p>
              <h3>{{ pendingRequestTitle }}</h3>
              <p class="relationship-space-detail__break-summary">{{ pendingRequestDescription }}</p>
            </div>
            <div class="relationship-space-detail__break-badges">
              <span v-if="pendingRequestPill" class="relationship-space-detail__status-pill">
                {{ pendingRequestPill }}
              </span>
              <span v-if="pendingRequestDeadline" class="relationship-space-detail__break-deadline">
                {{ pendingRequestDeadline }}
              </span>
            </div>
          </div>

          <div class="relationship-space-detail__break-body">
            <div class="relationship-space-detail__break-main">
              <section class="relationship-space-detail__break-section relationship-space-detail__break-section--timeline">
                <div class="relationship-space-detail__break-section-head">
                  <div>
                    <p class="eyebrow">流程</p>
                    <strong>移除关系进度</strong>
                  </div>
                </div>
                <div class="relationship-space-detail__break-stage-rail">
                  <div
                    v-for="(step, index) in breakWorkflowSteps"
                    :key="step.label"
                    class="relationship-space-detail__break-step"
                    :class="{
                      'is-active': step.state === 'active',
                      'is-done': step.state === 'done',
                    }"
                    >
                      <span>{{ String(index + 1).padStart(2, '0') }}</span>
                      <strong>{{ step.label }}</strong>
                    </div>
                </div>
              </section>

              <section
                v-if="isPendingBreakRequest && pendingBreakMessages.length"
                class="relationship-space-detail__break-section"
              >
                <div class="relationship-space-detail__break-section-head">
                  <div>
                    <p class="eyebrow">留痕记录</p>
                    <strong>留言</strong>
                  </div>
                  <span>{{ pendingBreakMessages.length }} 条</span>
                </div>
                <div class="relationship-space-detail__message-thread">
                  <div
                    v-for="message in pendingBreakMessages"
                    :key="message.id"
                    class="relationship-space-detail__message-item"
                    :class="{ 'is-mine': String(message.sender_user_id || '') === currentUserId }"
                  >
                    <strong>{{ message.sender_nickname || '对方' }}</strong>
                    <p>{{ message.message }}</p>
                    <span class="relationship-space-detail__message-time">{{ formatDateTime(message.created_at) }}</span>
                  </div>
                </div>
              </section>

              <div
                v-if="showRetentionAppendComposer"
                class="relationship-space-detail__inline-composer"
              >
                <div class="relationship-space-detail__composer-head">
                  <div>
                    <p class="eyebrow">继续补充</p>
                    <strong>还有话想说，可以继续追加</strong>
                  </div>
                </div>
                <label class="field">
                  <span>补充内容</span>
                  <textarea
                    v-model="retentionAppendDraft"
                    class="input relationship-space-detail__textarea"
                    rows="3"
                    maxlength="1000"
                    placeholder="补一句你还想说的话。"
                  />
                </label>
                <div class="relationship-space-detail__status-actions">
                  <button class="btn btn-primary btn-sm" type="button" :disabled="appendingRetentionMessage" @click="appendBreakMessage">
                    {{ appendingRetentionMessage ? '发送中...' : '追加留言' }}
                  </button>
                </div>
              </div>
            </div>

            <aside class="relationship-space-detail__break-aside">
              <section class="relationship-space-detail__break-focus">
                <p class="eyebrow">当前处理</p>
                <strong>{{ pendingBreakTurnTitle }}</strong>
              </section>

              <section class="relationship-space-detail__break-section relationship-space-detail__break-section--actions">
                <div class="relationship-space-detail__break-section-head">
                  <div>
                    <p class="eyebrow">下一步</p>
                    <strong>现在可执行的操作</strong>
                  </div>
                </div>
                <div class="relationship-space-detail__status-actions relationship-space-detail__status-actions--stacked">
                  <button
                    v-if="showBreakRetainChoiceActions && !showRetentionComposer"
                    class="btn btn-primary btn-sm"
                    type="button"
                    :disabled="submittingRetention || processingBreakDecision"
                    @click="openRetentionComposer"
                  >
                    我要挽留
                  </button>
                  <button
                    v-if="showBreakRetainChoiceActions"
                    class="btn btn-ghost btn-sm"
                    type="button"
                    :disabled="processingBreakDecision"
                    @click="handleDeclineBreakRequest"
                  >
                    {{ processingBreakDecision ? '处理中...' : '仍然移除' }}
                  </button>
                  <button
                    v-if="showBreakRetentionDecisionActions"
                    class="btn btn-primary btn-sm"
                    type="button"
                    :disabled="processingBreakDecision"
                    @click="handleBreakRetentionDecision('accept')"
                  >
                    {{ processingBreakDecision ? '处理中...' : '接受挽留' }}
                  </button>
                  <button
                    v-if="showBreakRetentionDecisionActions"
                    class="btn btn-ghost btn-sm"
                    type="button"
                    :disabled="processingBreakDecision"
                    @click="handleBreakRetentionDecision('reject')"
                  >
                    {{ processingBreakDecision ? '处理中...' : '仍然移除' }}
                  </button>
                  <button
                    v-if="canCancelPendingBreakRequest"
                    class="btn btn-ghost btn-sm"
                    type="button"
                    :disabled="cancellingBreakRequest"
                    @click="cancelPendingBreakRequest"
                  >
                    {{ cancellingBreakRequest ? '撤回中...' : '撤回申请' }}
                  </button>
                </div>
              </section>

              <div
                v-if="showRetentionComposer"
                class="relationship-space-detail__inline-composer relationship-space-detail__inline-composer--aside"
              >
                <div class="relationship-space-detail__composer-head">
                  <div>
                    <p class="eyebrow">第一条留言</p>
                    <strong>写一条留言</strong>
                  </div>
                </div>
                <label class="field">
                  <span>挽留内容</span>
                  <textarea
                    v-model="retentionDraft"
                    class="input relationship-space-detail__textarea"
                    rows="4"
                    maxlength="1000"
                    placeholder="写下你想说的话。"
                  />
                </label>
                <div class="relationship-space-detail__status-actions relationship-space-detail__status-actions--stacked">
                  <button class="btn btn-ghost btn-sm" type="button" :disabled="submittingRetention" @click="closeRetentionComposer">
                    先收起
                  </button>
                  <button class="btn btn-primary btn-sm" type="button" :disabled="submittingRetention" @click="submitBreakRetention">
                    {{ submittingRetention ? '发送中...' : '发送留言' }}
                  </button>
                </div>
              </div>
            </aside>
          </div>
        </template>

        <template v-else>
          <div class="relationship-space-detail__status-copy">
            <p class="eyebrow">{{ pendingRequestEyebrow }}</p>
            <h3>{{ pendingRequestTitle }}</h3>
            <p>{{ pendingRequestDescription }}</p>
          </div>

          <div class="relationship-space-detail__status-actions relationship-space-detail__status-actions--decision">
            <button
              v-if="showGenericDecisionActions"
              class="btn btn-primary btn-sm"
              type="button"
              :disabled="processingDecision"
              @click="handleRequestDecision('approve')"
            >
              {{ processingDecision ? '处理中...' : pendingApproveLabel }}
            </button>
            <button
              v-if="showGenericDecisionActions"
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="processingDecision"
              @click="handleRequestDecision('reject')"
            >
              暂不确认
            </button>
            <span v-if="pendingRequestPill" class="relationship-space-detail__status-pill">
              {{ pendingRequestPill }}
            </span>
          </div>
        </template>
      </article>

      <article v-if="latestRequestResult" class="relationship-space-detail__status-card">
        <p class="eyebrow">最近记录</p>
        <h3>最近一次处理结果</h3>
        <p>{{ latestRequestResult }}</p>
      </article>
    </section>

    <section v-if="pair" class="relationship-space-detail__hero">
      <article class="relationship-space-detail__hero-card relationship-space-detail__hero-card--main">
        <div class="relationship-space-detail__compact-head">
          <div>
            <span>{{ detailModel.hero.subtitle }}</span>
            <strong>{{ partnerRemarkLabel }}</strong>
          </div>
          <div class="relationship-space-detail__compact-actions">
            <button
              v-if="canEditPartnerNickname"
              class="btn btn-ghost btn-sm"
              type="button"
              @click="openNicknameEditor"
            >
              修改备注
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="router.push('/timeline')">
              看关系日历
            </button>
            <button
              v-if="pair.status === 'active'"
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="Boolean(pendingRequest)"
              @click="toggleTypeSwitcher"
            >
              关系类型
            </button>
            <button
              v-if="pair.status === 'active'"
              class="btn btn-ghost btn-sm relationship-space-detail__danger-button"
              type="button"
              :disabled="!canStartBreakRequest || submittingBreakRequest"
              @click="openBreakRequestModal"
            >
              移除关系
            </button>
          </div>
        </div>

        <div class="relationship-space-detail__hero-copy">
          <strong>{{ detailModel.hero.stageLabel }}</strong>
          <p v-if="detailModel.hero.summary">{{ detailModel.hero.summary }}</p>
        </div>

        <div v-if="typeSwitcherOpen" class="relationship-space-detail__type-switcher relationship-space-detail__type-switcher--compact">
          <button
            v-for="option in typeOptions"
            :key="option.value"
            class="relationship-space-detail__type-option"
            :class="{ active: option.value === selectedNextType }"
            type="button"
            @click="promptTypeChange(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </article>

      <article class="relationship-space-detail__hero-card relationship-space-detail__hero-card--score">
        <span>{{ detailScoreHeading }}</span>
        <strong>{{ detailScoreValue }}</strong>
        <p v-if="detailScoreNote">{{ detailScoreNote }}</p>
      </article>
    </section>

    <section v-if="pair" class="relationship-space-detail__grid">
      <article class="relationship-space-detail__card">
        <p class="eyebrow">最近动态</p>
        <h3>动态</h3>
        <div class="relationship-space-detail__moments">
          <div v-for="(moment, index) in detailModel.moments" :key="`${index}-${moment}`">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <p>{{ moment }}</p>
          </div>
        </div>
      </article>

      <article class="relationship-space-detail__card relationship-space-detail__task-card">
        <div class="relationship-space-detail__task-head">
          <div>
            <p class="eyebrow">{{ taskScopeTab === 'today' ? '今日安排' : '明日安排' }}</p>
            <h3>{{ taskCardTitle }}</h3>
              <button class="btn btn-ghost btn-sm" type="button" :disabled="taskLoading || Boolean(scheduleError)" @click="openScheduleAgent()">{{ taskScopeTab === 'today' ? '让 AI 帮我选一件' : '和 AI 商量明天' }}</button>
          </div>
          <div class="relationship-space-detail__task-switch" role="group" aria-label="安排日期切换">
            <button
              class="relationship-space-detail__task-switch-item"
              :class="{ active: taskScopeTab === 'today' }"
              :aria-pressed="taskScopeTab === 'today'"
              type="button"
              @click="setTaskScope('today')"
            >
              今天
            </button>
            <button
              class="relationship-space-detail__task-switch-item"
              :class="{ active: taskScopeTab === 'tomorrow' }"
              :aria-pressed="taskScopeTab === 'tomorrow'"
              type="button"
              @click="setTaskScope('tomorrow')"
            >
              明天
            </button>
          </div>
        </div>

        <div v-if="taskLoading" class="relationship-space-detail__task-empty">正在加载安排…</div>
        <div v-else-if="scheduleError" class="empty-state" role="alert">{{ scheduleError }} <button class="btn btn-ghost btn-sm" @click="loadDailyTasks">重试</button></div>
          <div v-else-if="taskCardItems.length" class="relationship-space-detail__task-list">
          <article
            v-for="task in taskCardItems"
            :key="task.id"
            class="relationship-space-detail__task-item"
          >
            <div>
              <strong>{{ task.title }}</strong>
              <p>{{ task.description || '先做一个轻一点的小动作。' }}</p>
            </div>
            <span class="pill pill--soft">{{ task.status === 'completed' ? '已完成' : task.importance_level === 'high' ? '先做这件' : '待完成' }}</span>
          </article>
        </div>
        <div v-else class="relationship-space-detail__task-empty">{{ taskScopeTab === 'today' ? '今天还没有安排' : '明天还没有安排' }}。</div>

        <div class="relationship-space-detail__actions">
          <button
            class="btn btn-primary btn-sm"
            type="button"
            @click="router.push({ path: '/challenges', query: { pair_id: pair?.id, scope: taskScopeTab } })"
          >
            {{ taskScopeTab === 'today' ? '打开今天安排' : '打开明天安排' }}
          </button>
          <button class="btn btn-ghost btn-sm" type="button" @click="router.push({ path: '/challenges', query: { pair_id: pair?.id, scope: taskScopeTab, panel: 'settings' } })">
            安排设置
          </button>
          <button class="btn btn-primary btn-sm" type="button" @click="router.push('/checkin')">去记录</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="router.push('/repair-protocol')">缓和建议</button>
        </div>
      </article>

    </section>

    <section v-else class="relationship-space-detail__empty">
      <p class="eyebrow">没找到这段关系</p>
      <h3>回关系页重新选</h3>
      <p>回到总览，重新选择要查看的关系。</p>
      <button class="btn btn-primary btn-sm" type="button" @click="router.push('/pair')">返回关系页</button>
    </section>

    <div
      v-if="typeConfirmOpen"
      class="relationship-space-detail__modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeTypeConfirm"
    >
      <section class="relationship-space-detail__modal-paper">
        <p class="eyebrow">确认切换</p>
        <h3>确定要切换成“{{ nextTypeLabel }}”吗？</h3>
        <p>双方确认后生效。</p>
        <div class="relationship-space-detail__modal-actions">
          <button class="btn btn-ghost" type="button" @click="closeTypeConfirm">先不改</button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="submittingTypeRequest"
            @click="submitTypeChangeRequest"
          >
            {{ submittingTypeRequest ? '提交中...' : '确认切换' }}
          </button>
        </div>
      </section>
    </div>

    <div
      v-if="breakRequestModalOpen"
      class="relationship-space-detail__modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeBreakRequestModal"
    >
      <section class="relationship-space-detail__modal-paper">
        <p class="eyebrow">移除关系</p>
        <h3>这次要不要给对方挽留机会？</h3>
        <div class="relationship-space-detail__choice-grid">
          <button
            class="relationship-space-detail__choice-card"
            :class="{ active: breakAllowRetention }"
            type="button"
            @click="breakAllowRetention = true"
          >
            <div class="relationship-space-detail__choice-head">
              <strong>给挽留机会</strong>
              <span>24 小时内回应</span>
            </div>
          </button>
          <button
            class="relationship-space-detail__choice-card"
            :class="{ active: !breakAllowRetention }"
            type="button"
            @click="breakAllowRetention = false"
          >
            <div class="relationship-space-detail__choice-head">
              <strong>不给挽留机会</strong>
              <span>自动解除</span>
            </div>
          </button>
        </div>
        <div class="relationship-space-detail__modal-actions">
          <button class="btn btn-ghost" type="button" :disabled="submittingBreakRequest" @click="closeBreakRequestModal">先取消</button>
          <button class="btn btn-primary" type="button" :disabled="submittingBreakRequest" @click="submitBreakRequest">
            {{ submittingBreakRequest ? '提交中...' : '确认发起移除申请' }}
          </button>
        </div>
      </section>
    </div>

    <div
      v-if="nicknameEditorOpen"
      class="relationship-space-detail__modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeNicknameEditor"
    >
      <section class="relationship-space-detail__modal-paper">
        <p class="eyebrow">对方备注</p>
        <h3>备注对方</h3>
        <label class="field relationship-space-detail__modal-field">
          <span>备注名</span>
          <input
            v-model="nicknameDraft"
            class="input"
            type="text"
            maxlength="50"
            placeholder="例如：伴侣 / 家人 / 朋友"
            @keydown.enter.prevent="savePartnerNickname"
          />
        </label>
        <div class="relationship-space-detail__modal-actions">
          <button class="btn btn-ghost" type="button" :disabled="savingNickname" @click="closeNicknameEditor">取消</button>
          <button class="btn btn-ghost" type="button" :disabled="savingNickname || !partnerNicknameValue" @click="clearPartnerNickname">
            清空备注
          </button>
          <button class="btn btn-primary" type="button" :disabled="savingNickname" @click="savePartnerNickname">
            {{ savingNickname ? '保存中...' : '保存备注' }}
          </button>
        </div>
      </section>
    </div>
    <ContextAgentDialog v-if="scheduleContext" :context="scheduleContext" @close="scheduleContext = null" />
  </div>
</template>

<script setup>
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import { buildDemoSchedule, buildScheduleContext, createLatestRequest, scheduleDate, demoScheduleCache } from '@/utils/taskSchedule'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { useUserStore } from '@/stores/user'
import { pairStatusLabel, relationshipTypeLabel, CREATABLE_RELATIONSHIP_TYPE_LABELS } from '@/utils/displayText'
import {
  breakRequestPhaseLabel,
  describePairChangeRequest,
  describePairChangeResult,
  isBreakRequest,
  isPairChangeRequestedByMe,
  isPairChangeWaitingForMe,
} from '@/utils/pairChangeRequests'
import { buildRelationshipSpaceDetailModel } from '@/utils/relationshipSpaceModel'
import { resolveRelationshipSpaceTheme } from '@/utils/relationshipTheme'
import { buildRelationshipSpaces, getPartnerDisplayName } from '@/utils/relationshipSpaces'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
function isoDate(offset = 0) {
  const now = new Date()
  const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
  const pad = (value) => String(value).padStart(2, '0')
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`
}

function buildDemoDailyTasksPayload(scope = 'today') {
  const saved = demoScheduleCache.read({ owner: userStore.me?.id || 'sample', pairId: pair.value?.id, date: scheduleDate(scope) })
  if (saved) return saved
  return { ...buildDemoSchedule(demoFixture.tasks, scope) }
}

const themeClass = computed(() => `relationship-space-detail--theme-${
  resolveRelationshipSpaceTheme(userStore.isDemoMode ? '' : userStore.me?.relationship_space_theme)
}`)
const dailyTasksPayload = ref({ tasks: [] })
const taskScopeTab = ref('today')
const taskLoading = ref(false)
const typeSwitcherOpen = ref(false)
const typeConfirmOpen = ref(false)
const breakRequestModalOpen = ref(false)
const breakAllowRetention = ref(true)
const showRetentionComposer = ref(false)
const retentionDraft = ref('')
const retentionAppendDraft = ref('')
const nicknameEditorOpen = ref(false)
const nicknameDraft = ref('')
const selectedNextType = ref('')
const processingDecision = ref(false)
const processingBreakDecision = ref(false)
const submittingTypeRequest = ref(false)
const submittingBreakRequest = ref(false)
const submittingRetention = ref(false)
const appendingRetentionMessage = ref(false)
const cancellingBreakRequest = ref(false)
const savingNickname = ref(false)
const clockNow = ref(Date.now())
let clockTimerId = null

const pairId = computed(() => String(route.params.pairId || userStore.currentPairId || ''))
const pair = computed(() =>
  userStore.pairs.find((item) => item.id === pairId.value) || null
)

const partnerName = computed(() => (pair.value ? getPartnerDisplayName(pair.value) : '对方'))
const partnerNicknameValue = computed(() => String(pair.value?.custom_partner_nickname || '').trim())
const partnerRemarkLabel = computed(() => partnerNicknameValue.value || partnerName.value)
const canEditPartnerNickname = computed(() => (
  pair.value?.status === 'active'
  && Boolean(pair.value?.partner_id || pair.value?.partner_nickname || pair.value?.partner_email || pair.value?.partner_phone)
))
const currentUserId = computed(() => String(userStore.me?.id || ''))
const pendingRequest = computed(() => pair.value?.pending_change_request || null)
const latestRequest = computed(() => pair.value?.latest_change_request || null)
const isPendingBreakRequest = computed(() => isBreakRequest(pendingRequest.value))
const pendingBreakPhase = computed(() => String(pendingRequest.value?.phase || '').trim())
const pendingBreakMessages = computed(() => Array.isArray(pendingRequest.value?.messages) ? pendingRequest.value.messages : [])
const latestRequestResult = computed(() => {
  if (!latestRequest.value || latestRequest.value.status === 'pending') return ''
  return describePairChangeResult(latestRequest.value)
})
const pendingRequestWaitingForMe = computed(() => isPairChangeWaitingForMe(pendingRequest.value, currentUserId.value))
const pendingRequestRequestedByMe = computed(() => isPairChangeRequestedByMe(pendingRequest.value, currentUserId.value))
const pendingBreakCanAppendMessage = computed(() => (
  isPendingBreakRequest.value
  && pendingBreakPhase.value === 'retaining'
  && String(pendingRequest.value?.approver_user_id || '') === currentUserId.value
))
const showGenericDecisionActions = computed(() => pendingRequestWaitingForMe.value && !isPendingBreakRequest.value)
const showBreakRetainChoiceActions = computed(() => (
  isPendingBreakRequest.value
  && pendingBreakPhase.value === 'awaiting_retention_choice'
  && pendingRequestWaitingForMe.value
))
const showBreakRetentionDecisionActions = computed(() => (
  isPendingBreakRequest.value
  && pendingBreakPhase.value === 'retaining'
  && pendingRequestWaitingForMe.value
))
const showRetentionAppendComposer = computed(() => pendingBreakCanAppendMessage.value)
const canStartBreakRequest = computed(() => pair.value?.status === 'active' && !pendingRequest.value)
const canCancelPendingBreakRequest = computed(() => (
  isPendingBreakRequest.value
  && pendingRequestRequestedByMe.value
  && pendingBreakPhase.value !== 'retaining'
))
const pendingRequestEyebrow = computed(() => {
  if (!pendingRequest.value) return '待确认'
  if (!isPendingBreakRequest.value) return '待确认'
  return breakRequestPhaseLabel(pendingBreakPhase.value)
})
const pendingRequestDeadline = computed(() => {
  if (!isPendingBreakRequest.value || !pendingRequest.value?.expires_at) return ''
  const diff = new Date(pendingRequest.value.expires_at).getTime() - clockNow.value
  if (!Number.isFinite(diff)) return ''
  if (diff <= 0) return '倒计时已到，重新进入页面后会自动结算'
  const totalMinutes = Math.ceil(diff / 60000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (pendingBreakPhase.value === 'retaining') {
    return `挽留阶段还剩 ${hours} 小时 ${minutes} 分钟`
  }
  return `当前阶段还剩 ${hours} 小时 ${minutes} 分钟`
})
const pendingRequestPill = computed(() => {
  if (!pendingRequest.value) return ''
  if (!isPendingBreakRequest.value) {
    return pendingRequestRequestedByMe.value ? '已提交，等待对方确认' : ''
  }
  if (pendingBreakPhase.value === 'awaiting_timeout') {
    return pendingRequestRequestedByMe.value ? '24 小时后自动解除' : '当前没有可选操作'
  }
  if (pendingBreakPhase.value === 'awaiting_retention_choice') {
    return pendingRequestRequestedByMe.value ? '等待对方决定是否挽留' : ''
  }
  if (pendingBreakPhase.value === 'retaining') {
    if (pendingRequestWaitingForMe.value) return ''
    return pendingRequestRequestedByMe.value ? '' : '还能继续追加留言'
  }
  return ''
})
const pendingApproveLabel = computed(() => pendingRequest.value?.kind === 'join_request' ? '确认建立关系' : '确认切换')
const pendingRequestTitle = computed(() => {
  if (!pendingRequest.value) return ''
  if (isPendingBreakRequest.value) {
    if (pendingBreakPhase.value === 'awaiting_timeout') {
      return pendingRequestRequestedByMe.value ? '你已发起移除关系申请' : '对方已发起移除关系申请'
    }
    if (pendingBreakPhase.value === 'awaiting_retention_choice') {
      return pendingRequestRequestedByMe.value ? '你已发起移除关系申请' : '对方希望移除这段关系'
    }
    if (pendingBreakPhase.value === 'retaining') {
      return pendingRequestWaitingForMe.value ? '对方正在挽留这段关系' : '你正在挽留这段关系'
    }
    return '这段关系正在处理中'
  }
  if (pendingRequestWaitingForMe.value) {
    return pendingRequest.value.kind === 'join_request' ? '对方已提交加入请求' : '对方申请切换关系类型'
  }
  if (pendingRequestRequestedByMe.value) {
    return pendingRequest.value.kind === 'join_request' ? '你已提交加入请求' : '你已提交类型切换请求'
  }
  return '这段关系有待确认事项'
})
const pendingRequestDescription = computed(() => {
  if (!pendingRequest.value) return ''
  if (isPendingBreakRequest.value) {
    if (pendingBreakPhase.value === 'awaiting_timeout') {
      return pendingRequestRequestedByMe.value
        ? '24 小时后自动解除。'
        : '对方未开放挽留，24 小时后自动解除。'
    }
    if (pendingBreakPhase.value === 'awaiting_retention_choice') {
      return pendingRequestWaitingForMe.value
        ? '24 小时内选择是否挽留。'
        : '等待对方选择是否挽留。'
    }
    if (pendingBreakPhase.value === 'retaining') {
      return pendingRequestWaitingForMe.value
        ? '对方已提交挽留。'
        : '已提交挽留。'
    }
  }
  const requestSummary = describePairChangeRequest(pendingRequest.value)
  if (pendingRequestWaitingForMe.value) {
    return `${requestSummary}。确认后生效。`
  }
  if (pendingRequestRequestedByMe.value) {
    return `${requestSummary}。等待对方确认。`
  }
  return requestSummary
})
const breakWorkflowSteps = computed(() => {
  if (!isPendingBreakRequest.value) return []
  const phase = pendingBreakPhase.value
  return [
    {
      label: '发起申请',
      note: pendingRequestRequestedByMe.value ? '你发起' : '对方发起',
      state: 'done',
    },
    {
      label: '是否挽留',
      note: phase === 'awaiting_timeout' ? '不挽留' : '等待选择',
      state: phase === 'awaiting_retention_choice' ? 'active' : phase === 'retaining' ? 'done' : 'done',
    },
    {
      label: '挽留阶段',
      note: phase === 'retaining' ? '处理中' : '未进入',
      state: phase === 'retaining' ? 'active' : 'idle',
    },
  ]
})
const pendingBreakTurnTitle = computed(() => {
  if (!isPendingBreakRequest.value) return ''
  if (pendingBreakPhase.value === 'awaiting_timeout') {
    return pendingRequestRequestedByMe.value ? '等待倒计时结束' : '等待系统自动解除'
  }
  if (pendingBreakPhase.value === 'awaiting_retention_choice') {
    return pendingRequestWaitingForMe.value ? '轮到你决定' : '等待对方回应'
  }
  if (pendingBreakPhase.value === 'retaining') {
    return pendingRequestWaitingForMe.value ? '轮到你做最终决定' : '等待对方做最终决定'
  }
  return '处理中'
})
const typeOptions = computed(() =>
  Object.entries(CREATABLE_RELATIONSHIP_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  }))
)
const nextTypeLabel = computed(() => relationshipTypeLabel(selectedNextType.value))

const detailMoments = computed(() => {
  if (!pair.value) return []

  if (userStore.isDemoMode) {
    return demoFixture.relationshipSpaces.find((space) => space.pair_id === pair.value.id)?.moments || []
  }

  return buildRelationshipSpaces({ pairs: [pair.value], me: userStore.me })[0]?.moments || []
})

const detailModel = computed(() =>
  buildRelationshipSpaceDetailModel({
    me: userStore.me,
    pair: pair.value,
    metricsByPairId: userStore.isDemoMode ? (demoFixture.relationshipMetrics || {}) : {},
    moments: detailMoments.value,
  })
)

const taskCardItems = computed(() => (dailyTasksPayload.value.tasks || []).slice(0, 6))
const taskCardTitle = computed(() => (
  taskScopeTab.value === 'today'
    ? '今天安排'
    : '明天安排'
))
const detailHasScore = computed(() => {
  const score = detailModel.value?.scoreCard?.score
  return score !== null && score !== undefined && score !== '' && Number.isFinite(Number(score))
})
const detailScoreHeading = computed(() => (detailHasScore.value ? '关系评分' : '关系状态'))
const detailScoreValue = computed(() => (
  detailHasScore.value
    ? String(detailModel.value?.scoreCard?.score ?? '')
    : String(detailModel.value?.scoreCard?.scoreLabel || pairStatusLabel(pair.value?.status))
))
const detailScoreNote = computed(() => {
  if (!detailHasScore.value) return ''
  return String(detailModel.value?.scoreCard?.trendLabel || '').trim()
})

watch(() => [pairId.value, pair.value?.status || ''], () => {
  loadDailyTasks()
  typeSwitcherOpen.value = false
  typeConfirmOpen.value = false
  breakRequestModalOpen.value = false
  showRetentionComposer.value = false
  retentionDraft.value = ''
  retentionAppendDraft.value = ''
  nicknameEditorOpen.value = false
  nicknameDraft.value = ''
})

watch(() => [pendingRequest.value?.id || '', pendingRequest.value?.phase || ''], () => {
  if (!pendingRequest.value || pendingRequest.value.phase !== 'awaiting_retention_choice') {
    showRetentionComposer.value = false
    retentionDraft.value = ''
  }
  if (!pendingRequest.value || pendingRequest.value.phase !== 'retaining') {
    retentionAppendDraft.value = ''
  }
})

onMounted(() => {
  loadDailyTasks()
  clockTimerId = window.setInterval(() => {
    clockNow.value = Date.now()
  }, 30000)
})

onBeforeUnmount(() => {
  if (clockTimerId) {
    window.clearInterval(clockTimerId)
    clockTimerId = null
  }
})

async function loadDailyTasks() {
  const current = scheduleRequests.begin()
  const requestScope = taskScopeTab.value
  const requestPair = pair.value?.id
  taskLoading.value = false
  scheduleError.value = ''
  dailyTasksPayload.value = { tasks: [] }
  if (!(pair.value?.id && pair.value?.status === 'active')) return
  if (userStore.isDemoMode) {
    dailyTasksPayload.value = buildDemoDailyTasksPayload(requestScope)
    return
  }
  taskLoading.value = true
  try {
    const result = await api.getDailyTasks(requestPair, { forDate: scheduleDate(requestScope), dateScope: requestScope })
    if (current()) dailyTasksPayload.value = result
  } catch (error) {
    if (current()) scheduleError.value = error.message || '安排没加载出来，请重试'
  } finally {
    if (current()) taskLoading.value = false
  }
}

function setTaskScope(scope) {
  taskScopeTab.value = scope === 'tomorrow' ? 'tomorrow' : 'today'
  loadDailyTasks()
}

function toggleTypeSwitcher() {
  if (pendingRequest.value) return
  typeSwitcherOpen.value = !typeSwitcherOpen.value
}

function promptTypeChange(nextType) {
  if (!pair.value || pair.value.status !== 'active') return
  if (pendingRequest.value) return
  if (String(nextType || '') === String(pair.value.type || '')) return
  selectedNextType.value = String(nextType || '')
  typeConfirmOpen.value = true
}

function closeTypeConfirm() {
  typeConfirmOpen.value = false
  selectedNextType.value = ''
}

function openBreakRequestModal() {
  if (!canStartBreakRequest.value) return
  breakAllowRetention.value = true
  breakRequestModalOpen.value = true
}

function closeBreakRequestModal() {
  breakRequestModalOpen.value = false
  breakAllowRetention.value = true
}

function openRetentionComposer() {
  if (!showBreakRetainChoiceActions.value) return
  showRetentionComposer.value = true
}

function closeRetentionComposer() {
  showRetentionComposer.value = false
  retentionDraft.value = ''
}

function openNicknameEditor() {
  if (!canEditPartnerNickname.value) return
  nicknameDraft.value = partnerNicknameValue.value
  nicknameEditorOpen.value = true
}

function closeNicknameEditor() {
  nicknameEditorOpen.value = false
  nicknameDraft.value = partnerNicknameValue.value
}

async function submitTypeChangeRequest() {
  if (!pair.value?.id || !selectedNextType.value) return

  submittingTypeRequest.value = true
  try {
    await userStore.requestPairTypeChange(pair.value.id, selectedNextType.value)
    typeSwitcherOpen.value = false
    closeTypeConfirm()
    showToast('已提交切换请求，等对方确认后才会正式生效')
  } catch (e) {
    showToast(e.message || '切换请求没有提交成功，请稍后再试')
  } finally {
    submittingTypeRequest.value = false
  }
}

async function submitBreakRequest() {
  if (!pair.value?.id || submittingBreakRequest.value) return

  submittingBreakRequest.value = true
  try {
    await userStore.createBreakRequest(pair.value.id, breakAllowRetention.value)
    closeBreakRequestModal()
    showToast(
      breakAllowRetention.value
        ? '已发起移除关系申请，对方可以在 24 小时内选择是否挽留'
        : '已发起移除关系申请，这段关系会在 24 小时后自动解除'
    )
  } catch (e) {
    showToast(e.message || '移除关系申请没有提交成功，请稍后再试')
  } finally {
    submittingBreakRequest.value = false
  }
}

async function submitBreakRetention() {
  if (!pair.value?.id || !pendingRequest.value?.id) return
  const trimmedMessage = String(retentionDraft.value || '').trim()
  if (!trimmedMessage) {
    showToast('先写一句挽留')
    return
  }

  submittingRetention.value = true
  try {
    await userStore.retainBreakRequest(pair.value.id, pendingRequest.value.id, trimmedMessage)
    closeRetentionComposer()
    showToast('挽留已提交，进入 12 小时挽留阶段')
  } catch (e) {
    showToast(e.message || '挽留没提交上，请稍后再试')
  } finally {
    submittingRetention.value = false
  }
}

async function appendBreakMessage() {
  if (!pair.value?.id || !pendingRequest.value?.id) return
  const trimmedMessage = String(retentionAppendDraft.value || '').trim()
  if (!trimmedMessage) {
    showToast('先写一点你想补充的话')
    return
  }

  appendingRetentionMessage.value = true
  try {
    await userStore.appendBreakRequestMessage(pair.value.id, pendingRequest.value.id, trimmedMessage)
    retentionAppendDraft.value = ''
    showToast('已追加挽留')
  } catch (e) {
    showToast(e.message || '留言没有发送成功，请稍后再试')
  } finally {
    appendingRetentionMessage.value = false
  }
}

async function handleDeclineBreakRequest() {
  if (!pair.value?.id || !pendingRequest.value?.id) return

  processingBreakDecision.value = true
  try {
    const res = await userStore.declineBreakRequest(pair.value.id, pendingRequest.value.id)
    showToast('已选择仍然移除，这段关系现已解除')
    if (res?.pair?.status === 'ended') {
      router.push('/pair')
    }
  } catch (e) {
    showToast(e.message || '这次处理没有成功，请稍后再试')
  } finally {
    processingBreakDecision.value = false
  }
}

async function handleBreakRetentionDecision(decision) {
  if (!pair.value?.id || !pendingRequest.value?.id) return

  processingBreakDecision.value = true
  try {
    const res = await userStore.decideBreakRequestRetention(pair.value.id, pendingRequest.value.id, decision)
    if (decision === 'accept') {
      showToast('你已接受挽留，关系恢复正常，这条记录会留在后台')
    } else {
      showToast('你已选择仍然移除，这段关系现已解除')
    }
    if (res?.pair?.status === 'ended') {
      router.push('/pair')
    }
  } catch (e) {
    showToast(e.message || '这次处理没有成功，请稍后再试')
  } finally {
    processingBreakDecision.value = false
  }
}

async function handleRequestDecision(decision) {
  if (!pair.value?.id || !pendingRequest.value?.id) return

  processingDecision.value = true
  try {
    await userStore.decidePairChangeRequest(pair.value.id, pendingRequest.value.id, decision)
    showToast(decision === 'approve' ? '已确认，这次变更现在正式生效' : '已记录为暂不确认')
  } catch (e) {
    showToast(e.message || '这次处理没有成功，请稍后再试')
  } finally {
    processingDecision.value = false
  }
}

async function cancelPendingBreakRequest() {
  if (!pair.value?.id || !pendingRequest.value?.id) return

  cancellingBreakRequest.value = true
  try {
    await userStore.cancelPairChangeRequest(pair.value.id, pendingRequest.value.id)
    showToast('这次移除关系申请已撤回')
  } catch (e) {
    showToast(e.message || '撤回没有成功，请稍后再试')
  } finally {
    cancellingBreakRequest.value = false
  }
}

async function savePartnerNickname() {
  if (!pair.value?.id || !canEditPartnerNickname.value) return

  savingNickname.value = true
  try {
    const trimmedNickname = String(nicknameDraft.value || '').trim()
    await userStore.updatePartnerNickname(pair.value.id, trimmedNickname)
    nicknameDraft.value = trimmedNickname
    nicknameEditorOpen.value = false
    showToast(trimmedNickname ? '备注已更新' : '备注已清空')
  } catch (e) {
    showToast(e.message || '备注没有保存成功，请稍后再试')
  } finally {
    savingNickname.value = false
  }
}

async function clearPartnerNickname() {
  nicknameDraft.value = ''
  await savePartnerNickname()
}

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  const hour = `${date.getHours()}`.padStart(2, '0')
  const minute = `${date.getMinutes()}`.padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}
const scheduleContext = ref(null)
const scheduleRequests = createLatestRequest()
const scheduleError = ref('')
function openScheduleAgent(task = null) {
  scheduleContext.value = buildScheduleContext(task ? [task] : taskCardItems.value, {
    scope: taskScopeTab.value, date: scheduleDate(taskScopeTab.value), pairId: pair.value?.id || null,
    isDemoMode: userStore.isDemoMode, single: Boolean(task),
  })
}
watch(() => [userStore.token, userStore.me?.id, pair.value?.id, taskScopeTab.value], () => {
  scheduleRequests.invalidate()
  scheduleContext.value = null
  dailyTasksPayload.value = { tasks: [] }
  taskLoading.value = false
}, { flush: 'sync' })
watch(() => [userStore.token, userStore.me?.id], () => loadDailyTasks())
onBeforeUnmount(() => scheduleRequests.invalidate())

</script>

<style scoped>
.relationship-space-detail {
  --relationship-space-glow-a: rgba(223, 154, 125, 0.16);
  --relationship-space-glow-b: rgba(168, 201, 208, 0.22);
  --relationship-space-glow-c: rgba(240, 184, 116, 0.16);
  --relationship-space-surface-start: var(--relationship-night-900);
  --relationship-space-surface-mid: var(--relationship-night-700);
  --relationship-space-surface-end: var(--relationship-night-500);
  --relationship-space-card: rgba(255, 250, 244, 0.74);
  gap: 16px;
  padding-bottom: 32px;
}

.relationship-space-detail__status-strip {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
}

.relationship-space-detail__status-strip--split {
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.8fr);
}

.relationship-space-detail__status-strip--break {
  grid-template-columns: minmax(0, 1fr);
}

.relationship-space-detail__status-card,
.relationship-space-detail__hero-card,
.relationship-space-detail__card,
.relationship-space-detail__empty {
  padding: 20px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(249, 245, 239, 0.9)),
    rgba(255, 255, 255, 0.56);
  box-shadow: 0 14px 32px rgba(56, 42, 30, 0.05);
}

.relationship-space-detail__status-card {
  display: grid;
  gap: 10px;
}

.relationship-space-detail__status-card--pending {
  background: linear-gradient(180deg, rgba(255, 247, 239, 0.96), rgba(255, 252, 248, 0.94));
}

.relationship-space-detail__status-card--generic {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px 24px;
  align-items: center;
  min-height: 132px;
  background:
    radial-gradient(circle at top right, rgba(189, 75, 53, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(255, 247, 239, 0.98), rgba(255, 252, 248, 0.94));
}

.relationship-space-detail__status-card--break {
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(255, 221, 206, 0.46), transparent 28%),
    linear-gradient(180deg, rgba(255, 247, 241, 0.98), rgba(255, 252, 248, 0.94));
}

.relationship-space-detail__status-card--retaining {
  background:
    radial-gradient(circle at top right, rgba(226, 199, 170, 0.36), transparent 28%),
    linear-gradient(180deg, rgba(255, 249, 241, 0.98), rgba(255, 252, 248, 0.94));
}

.relationship-space-detail__status-card h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 26px;
  line-height: 1.35;
}

.relationship-space-detail__status-copy {
  display: grid;
  gap: 8px;
}

.relationship-space-detail__status-copy p {
  margin: 0;
}

.relationship-space-detail__status-card p,
.relationship-space-detail__lead,
.relationship-space-detail__modal-paper p {
  color: rgba(95, 71, 60, 0.84);
  font-size: 14px;
  line-height: 1.75;
}

.relationship-space-detail__status-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.relationship-space-detail__status-actions--decision {
  min-width: 220px;
  justify-content: flex-end;
  align-items: center;
}

.relationship-space-detail__status-actions--stacked {
  display: grid;
  grid-template-columns: 1fr;
}

.relationship-space-detail__status-actions--stacked .btn {
  width: 100%;
}

.relationship-space-detail__break-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
}

.relationship-space-detail__break-header-copy {
  display: grid;
  gap: 8px;
}

.relationship-space-detail__break-badges {
  display: grid;
  justify-items: end;
  gap: 8px;
}

.relationship-space-detail__break-summary {
  margin: 0;
}

.relationship-space-detail__break-deadline {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: var(--radius-lg);
  background: rgba(170, 77, 51, 0.08);
  color: #8b4334;
  font-size: 12px;
  font-weight: 700;
}

.relationship-space-detail__break-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.42fr);
  gap: 16px;
  align-items: start;
}

.relationship-space-detail__break-main,
.relationship-space-detail__break-aside {
  display: grid;
  gap: 14px;
}

.relationship-space-detail__break-aside {
  align-self: stretch;
}

.relationship-space-detail__break-stage-rail {
  display: grid;
  gap: 10px;
}

.relationship-space-detail__break-section--timeline .relationship-space-detail__break-stage-rail {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.relationship-space-detail__break-step,
.relationship-space-detail__break-focus,
.relationship-space-detail__break-section {
  padding: 13px 14px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(68, 52, 40, 0.08);
  background: rgba(255, 255, 255, 0.72);
}

.relationship-space-detail__break-step {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 4px 12px;
  align-items: start;
}

.relationship-space-detail__break-step span {
  grid-row: span 2;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-lg);
  background: rgba(132, 150, 205, 0.1);
  color: #546689;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.relationship-space-detail__break-step strong,
.relationship-space-detail__break-focus strong,
.relationship-space-detail__composer-head strong,
.relationship-space-detail__break-section-head strong {
  color: var(--ink);
  font-size: 16px;
  line-height: 1.5;
}

.relationship-space-detail__composer-head span,
.relationship-space-detail__break-section-head span {
  color: rgba(95, 71, 60, 0.72);
  font-size: 12px;
  line-height: 1.6;
}

.relationship-space-detail__break-step.is-active {
  border-color: rgba(189, 75, 53, 0.18);
  background: linear-gradient(180deg, rgba(255, 247, 241, 0.96), rgba(255, 252, 248, 0.94));
}

.relationship-space-detail__break-step.is-active span {
  background: rgba(189, 75, 53, 0.12);
  color: #9a4631;
}

.relationship-space-detail__break-step.is-done span {
  background: rgba(104, 165, 124, 0.12);
  color: #3f7c56;
}

.relationship-space-detail__break-focus {
  display: grid;
  gap: 8px;
  align-content: start;
  background: linear-gradient(180deg, rgba(255, 251, 247, 0.94), rgba(252, 246, 241, 0.94));
}

.relationship-space-detail__break-section {
  display: grid;
  gap: 12px;
}

.relationship-space-detail__break-section--actions {
  background: rgba(255, 252, 248, 0.84);
}

.relationship-space-detail__break-section--actions .relationship-space-detail__break-section-head {
  padding-bottom: 2px;
}

.relationship-space-detail__break-section-head,
.relationship-space-detail__composer-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.relationship-space-detail__inline-composer {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(68, 52, 40, 0.08);
  background: rgba(255, 255, 255, 0.78);
}

.relationship-space-detail__inline-composer--aside {
  background: rgba(255, 249, 244, 0.9);
}

.relationship-space-detail__textarea {
  min-height: 112px;
  resize: vertical;
}

.relationship-space-detail__message-thread {
  display: grid;
  gap: 10px;
}

.relationship-space-detail__message-item {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
}

.relationship-space-detail__message-item.is-mine {
  background: rgba(255, 247, 241, 0.92);
}

.relationship-space-detail__message-item strong {
  color: var(--ink);
  font-size: 13px;
}

.relationship-space-detail__message-item p {
  margin: 0;
}

.relationship-space-detail__message-time {
  color: rgba(95, 71, 60, 0.68);
  font-size: 12px;
}

.relationship-space-detail__status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(132, 150, 205, 0.14);
  color: #4a5d8a;
  font-size: 13px;
  font-weight: 700;
}

.relationship-space-detail__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(240px, 0.8fr);
  gap: 16px;
}

.relationship-space-detail__hero-card--main {
  display: grid;
  gap: 16px;
  align-content: start;
  color: var(--relationship-ink-700);
  background:
    linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(249, 245, 239, 0.9)),
    rgba(255, 255, 255, 0.56);
  box-shadow: 0 12px 28px rgba(170, 77, 51, 0.06);
}

.relationship-space-detail__compact-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}

.relationship-space-detail__compact-head span {
  color: rgba(95, 71, 60, 0.68);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.relationship-space-detail__compact-head strong {
  display: block;
  margin-top: 6px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 24px;
  line-height: 1.35;
}

.relationship-space-detail__compact-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.relationship-space-detail__hero-copy {
  display: grid;
  gap: 8px;
}

.relationship-space-detail__hero-card span,
.relationship-space-detail__card .eyebrow,
.relationship-space-detail__status-card .eyebrow,
.relationship-space-detail__modal-paper .eyebrow {
  color: var(--seal);
}

.relationship-space-detail__hero-copy strong,
.relationship-space-detail__hero-card--score strong {
  display: block;
  margin-top: 8px;
  font-family: var(--font-serif);
  font-size: 30px;
  line-height: 1.4;
}

.relationship-space-detail__hero-card p {
  margin-top: 8px;
  color: rgba(95, 71, 60, 0.84);
  font-size: 14px;
  line-height: 1.75;
}

.relationship-space-detail__hero-card--score {
  display: grid;
  align-content: center;
  justify-items: start;
}

.relationship-space-detail__danger-button {
  border-color: rgba(170, 77, 51, 0.22);
  color: #9d3d2c;
}

.relationship-space-detail__type-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.relationship-space-detail__type-switcher--compact {
  padding-top: 4px;
}

.relationship-space-detail__type-option {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.68);
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.relationship-space-detail__type-option:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
}

.relationship-space-detail__type-option.active {
  border-color: rgba(189, 75, 53, 0.3);
  background: var(--seal-soft);
  color: var(--seal-deep);
}

.relationship-space-detail__grid {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
  gap: 16px;
  align-items: start;
}

.relationship-space-detail__moments {
  display: grid;
  gap: 12px;
}

.relationship-space-detail__moments div {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.relationship-space-detail__moments span {
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 800;
}

.relationship-space-detail__moments p {
  margin: 0;
}

.relationship-space-detail__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.relationship-space-detail__modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(29, 20, 16, 0.38);
  backdrop-filter: blur(10px);
}

.relationship-space-detail__modal-paper {
  width: min(100%, 560px);
  display: grid;
  gap: 14px;
  padding: 24px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(68, 52, 40, 0.08);
  background: linear-gradient(180deg, rgba(255, 252, 248, 0.98), rgba(250, 244, 237, 0.96));
  box-shadow: 0 24px 54px rgba(28, 18, 13, 0.18);
}

.relationship-space-detail__modal-paper h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 30px;
  line-height: 1.35;
}

.relationship-space-detail__modal-field {
  display: grid;
  gap: 8px;
}

.relationship-space-detail__modal-field span {
  color: rgba(95, 71, 60, 0.82);
  font-size: 13px;
  font-weight: 700;
}

.relationship-space-detail__modal-tip {
  margin: -4px 0 0;
  color: rgba(95, 71, 60, 0.68);
  font-size: 12px;
}

.relationship-space-detail__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.relationship-space-detail__choice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.relationship-space-detail__choice-card {
  display: grid;
  gap: 8px;
  min-height: 118px;
  padding: 14px;
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.72);
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.relationship-space-detail__choice-card:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
  box-shadow: 0 10px 22px rgba(170, 77, 51, 0.05);
}

.relationship-space-detail__choice-card.active {
  border-color: rgba(189, 75, 53, 0.28);
  background: rgba(255, 247, 241, 0.96);
}

.relationship-space-detail__choice-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.relationship-space-detail__choice-head span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-lg);
  background: rgba(132, 150, 205, 0.12);
  color: #546689;
  font-size: 11px;
  font-weight: 800;
}

.relationship-space-detail__choice-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
  color: rgba(95, 71, 60, 0.78);
  font-size: 13px;
  line-height: 1.6;
}

.relationship-space-detail--theme-stardust {
  --relationship-space-glow-a: rgba(206, 173, 233, 0.18);
  --relationship-space-glow-b: rgba(202, 222, 255, 0.24);
  --relationship-space-glow-c: rgba(240, 188, 142, 0.14);
  --relationship-space-surface-start: #fffaf4;
  --relationship-space-surface-mid: #f6f0ee;
  --relationship-space-surface-end: #efe6df;
  --relationship-space-card: rgba(255, 249, 245, 0.76);
}

.relationship-space-detail--theme-engine {
  --relationship-space-glow-a: rgba(255, 185, 112, 0.18);
  --relationship-space-glow-b: rgba(170, 235, 244, 0.26);
  --relationship-space-glow-c: rgba(255, 226, 196, 0.16);
  --relationship-space-surface-start: #fff9f2;
  --relationship-space-surface-mid: #f3efe8;
  --relationship-space-surface-end: #ebe4d8;
  --relationship-space-card: rgba(248, 252, 252, 0.78);
}

@media (max-width: 1100px) {
  .relationship-space-detail__status-strip,
  .relationship-space-detail__hero,
  .relationship-space-detail__grid {
    grid-template-columns: 1fr;
  }

  .relationship-space-detail__break-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .relationship-space-detail__hero-card,
  .relationship-space-detail__card,
  .relationship-space-detail__empty,
  .relationship-space-detail__status-card {
    padding: 18px;
    border-radius: var(--radius-lg);
  }

  .relationship-space-detail__break-section--timeline .relationship-space-detail__break-stage-rail,
  .relationship-space-detail__choice-grid {
    grid-template-columns: 1fr;
  }

  .relationship-space-detail__modal-paper {
    padding: 20px;
    border-radius: var(--radius-lg);
  }

  .relationship-space-detail__break-header {
    grid-template-columns: 1fr;
  }

  .relationship-space-detail__status-card--generic {
    grid-template-columns: 1fr;
    min-height: 0;
  }

  .relationship-space-detail__status-actions--decision {
    min-width: 0;
    justify-content: flex-start;
  }

  .relationship-space-detail__break-badges {
    justify-items: start;
  }

.relationship-space-detail__modal-paper h3 {
  font-size: 26px;
}
}

.relationship-space-detail__task-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.relationship-space-detail__task-switch {
  display: inline-flex;
  padding: 4px;
  border-radius: var(--radius-lg);
  background: rgba(76, 118, 106, 0.08);
  gap: 4px;
}

.relationship-space-detail__task-switch-item {
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  padding: 8px 14px;
  border-radius: var(--radius-lg);
  cursor: pointer;
}

.relationship-space-detail__task-switch-item.active {
  background: rgba(255, 255, 255, 0.9);
  color: var(--ink);
}

.relationship-space-detail__task-note {
  margin: 12px 0 0;
  color: var(--ink-soft);
}

.relationship-space-detail__task-list {
  margin-top: 16px;
  display: grid;
  gap: 10px;
  max-height: 280px;
  overflow: auto;
}

.relationship-space-detail__task-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(76, 118, 106, 0.1);
}

.relationship-space-detail__task-item p,
.relationship-space-detail__task-empty {
  margin: 6px 0 0;
  color: var(--ink-soft);
}

@media (max-width: 560px) {
  .relationship-space-detail__status-actions,
  .relationship-space-detail__actions,
  .relationship-space-detail__modal-actions {
    grid-template-columns: 1fr;
    display: grid;
  }

  .relationship-space-detail__status-actions .btn,
  .relationship-space-detail__actions .btn,
  .relationship-space-detail__modal-actions .btn {
    width: 100%;
  }

  .relationship-space-detail__task-item {
    flex-direction: column;
  }
}
</style>

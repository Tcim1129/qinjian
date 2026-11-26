<template>
  <div class="coach-page">
    <div class="page-head coach-head">
      <div>
        <p class="eyebrow">发前看看</p>
        <h2>这句话怎么说</h2>
      </div>
      <div class="coach-head__actions">
        <button class="btn btn-ghost btn-sm" :disabled="loading" @click="handleRefreshPreview">{{ refreshButtonLabel }}</button>
        <button class="btn btn-ghost btn-sm" @click="$router.push('/alignment')">{{ alignmentButtonLabel }}</button>
      </div>
    </div>

    <section class="coach-input card">
      <div class="coach-input__main">
        <div class="card-header">
          <div>
            <p class="eyebrow">准备发的话</p>
            <h3>想发什么？</h3>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="loading" @click="runSimulation">
            {{ loading ? '查看中...' : analyzeButtonLabel }}
          </button>
        </div>

        <div class="coach-quick-chips">
          <span class="coach-quick-chips__hint">选择示例：</span>
          <button
            type="button"
            class="coach-quick-chip"
            @click="applyQuickDraft('你今天怎么又这么晚才回我，我真的很烦。')"
          >
            催回消息
          </button>
          <button
            type="button"
            class="coach-quick-chip"
            @click="applyQuickDraft('天天碗就堆在水槽里，每次都要我说你才动，真服了。')"
          >
            家务抱怨
          </button>
          <button
            type="button"
            class="coach-quick-chip"
            @click="applyQuickDraft('说好周末一起出去又加班，你心里根本没有把我们安排当回事吧。')"
          >
            临时爽约
          </button>
          <button
            v-if="previousDraftBeforeExample !== null"
            type="button"
            class="coach-quick-chip coach-quick-chip--undo"
            @click="undoQuickDraft"
          >
            撤回原草稿
          </button>
        </div>

        <label class="field">
          <span>原句</span>
          <textarea
            v-model="draft"
            class="input input-textarea coach-input__textarea"
            rows="5"
            placeholder="粘贴或输入准备发出的消息"
          ></textarea>
        </label>

        <div class="coach-voice-row" aria-live="polite">
          <div v-if="voicePreview || voiceStatus" class="coach-voice-status">
            <span v-if="voiceActive" class="coach-voice-pulse" aria-hidden="true"></span>
            <span v-else class="coach-voice-dot" aria-hidden="true"></span>
            <p>{{ voicePreview || voiceStatus }}</p>
          </div>
          <button
            class="coach-voice-button"
            type="button"
            :class="{ 'coach-voice-button--active': voiceActive || voiceStarting || voiceFinalizing }"
            :disabled="loading || voiceFinalizing"
            :aria-label="voiceActive || voiceFinalizing ? '停止转写' : voiceStarting ? '取消开启麦克风' : '语音转文字'"
            :title="voiceActive || voiceFinalizing ? '停止转写' : voiceStarting ? '取消开启麦克风' : '语音转文字'"
            @click="toggleVoiceInput"
          >
            <Loader2 v-if="voiceFinalizing || voiceStarting" :size="17" class="spin-icon" />
            <StopCircle v-else-if="voiceActive" :size="18" />
            <Mic v-else :size="18" />
            <span>{{ voiceButtonLabel }}</span>
          </button>
        </div>

        <div class="coach-input__footer">
          <span class="coach-privacy-note">点“看看这句”不会把消息发给对方</span>
          <div class="coach-input__footer-right">
            <span>{{ draftLength ? `已输入 ${draftLength} 字` : '把准备发的话写下来，先不着急点发送' }}</span>
            <button
              v-if="draftLength && !experienceMode.isDemoMode"
              type="button"
              class="coach-clear-draft"
              @click="clearDraftWorkspace"
            >
              清空
            </button>
          </div>
        </div>
      </div>
    </section>

    <template v-if="result">
      <div v-if="isResultStaleForDraft" class="coach-stale-banner" role="status">
        <div class="coach-stale-banner__text">
          <strong>原句已修改</strong>
          <p>下方仍是上一句的分析结果。重新分析当前内容后，再改写、复制或提交反馈。</p>
        </div>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="loading"
          @click="runSimulation"
        >
          {{ loading ? '查看中...' : '重新看看这句' }}
        </button>
      </div>

      <section class="coach-results" :class="{ 'coach-results--stale': isResultStaleForDraft }">
        <article class="card card-accent coach-risk-card" :class="riskClass">
          <div class="card-header">
            <div>
              <p class="eyebrow">表达评估</p>
              <h3>{{ riskLabel }}</h3>
            </div>
            <button
              class="btn btn-ghost btn-xs btn-adjust-judgment"
              type="button"
              :disabled="isResultStaleForDraft"
              @click="adjustPanelOpen = !adjustPanelOpen"
            >
              <SlidersHorizontal :size="13" />
              <span>{{ adjustPanelOpen ? '收起调整' : '调整判断' }}</span>
            </button>
          </div>
          <div class="coach-risk-split">
            <div class="coach-risk-split__item">
              <span class="coach-risk-split__label">施压风险</span>
              <strong :class="pressureRiskClass">{{ pressureRiskLabel }}</strong>
            </div>
            <div class="coach-risk-split__item">
              <span class="coach-risk-split__label">对话升级提醒</span>
              <strong :class="frictionRiskClass">{{ escalationFrictionLabel }}</strong>
            </div>
          </div>
          <p>{{ result.risk_reason }}</p>
          <ul v-if="escalationCues.length" class="coach-escalation-cues">
            <li v-for="cue in escalationCues" :key="cue">{{ cue }}</li>
          </ul>
          <div class="coach-risk-card__meta">
            <span>{{ baselineLabel }}</span>
            <span v-if="showReactionShiftPill">{{ reactionShiftLabel }}</span>
          </div>
        </article>

        <article class="card coach-result-card">
          <p class="eyebrow">对方可能怎么理解</p>
          <h3>{{ result.partner_view }}</h3>
          <p>{{ result.likely_impact }}</p>
        </article>

        <article v-if="result.rewrite_blocked" class="card coach-rewrite-card" role="status">
          <h3>先停止施压</h3>
          <p>{{ result.rewrite_block_reason }}</p>
        </article>
        <article v-else class="card coach-rewrite-card">
          <div class="card-header">
            <div>
              <p class="eyebrow">推荐改写</p>
              <h3>可以这样说</h3>
            </div>
            <div class="coach-rewrite-actions">
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="!currentSaferRewrite || isResultStaleForDraft || loading"
                @click="copyRewrite"
              >
                <Check v-if="copiedRewrite" :size="14" />
                <Copy v-else :size="14" />
                <span>{{ copiedRewrite ? '已复制' : '复制改写' }}</span>
              </button>
              <button
                class="btn btn-secondary btn-sm"
                type="button"
                :disabled="!currentSaferRewrite || isResultStaleForDraft || loading"
                @click="sendRewriteToChat"
              >
                <span>带去聊一聊</span>
              </button>
              <button
                class="btn btn-ghost btn-sm btn-regenerate"
                type="button"
                :disabled="refreshingRewrite || loading || isResultStaleForDraft"
                @click="handleRefreshRewrite"
                title="换一种表达思路"
              >
                <RefreshCw :size="14" :class="{ 'is-spinning': refreshingRewrite }" />
                <span>{{ refreshingRewrite ? '构思中...' : '换个改法' }}</span>
              </button>
            </div>
          </div>
          <blockquote>{{ currentSaferRewrite }}</blockquote>
          <div class="coach-inline-meta">
            <span>{{ result.conversation_goal }}</span>
            <span>{{ result.suggested_tone }}</span>
            <span>{{ confidenceLabel }}</span>
          </div>
        </article>
      </section>

      <section class="coach-actions card" :class="{ 'coach-results--stale': isResultStaleForDraft }">
        <div class="coach-actions__column">
          <p class="eyebrow">建议做</p>
          <ul class="plain-list">
            <li v-for="item in result.do_list" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="coach-actions__column coach-actions__column--muted">
          <p class="eyebrow">先别做</p>
          <ul class="plain-list">
            <li v-for="item in result.avoid_list" :key="item">{{ item }}</li>
          </ul>
        </div>
      </section>

      <section v-if="displayDeviationReasons.length" class="coach-secondary card" :class="{ 'coach-results--stale': isResultStaleForDraft }">
        <p class="eyebrow">和平时有什么不同</p>
        <ul class="plain-list">
          <li v-for="item in displayDeviationReasons" :key="item">{{ item }}</li>
        </ul>
      </section>

      <details class="coach-feedback card" :open="adjustPanelOpen">
        <summary @click.prevent="adjustPanelOpen = !adjustPanelOpen">调整系统判断与反馈</summary>
        <p class="coach-feedback__desc">如果觉得系统判断的风险偏高、或理解与实际情况不符，请在此修正并提交：</p>
        <div class="feedback-row">
          <button
            v-for="option in feedbackOptions"
            :key="option.value"
            type="button"
            class="btn btn-ghost btn-sm"
            :class="{ active: selectedFeedbackType === option.value }"
            :disabled="isResultStaleForDraft"
            @click="selectedFeedbackType = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <label class="field">
          <span>调整说明与备注</span>
          <textarea
            v-model="feedbackNote"
            class="input input-textarea"
            rows="3"
            :disabled="isResultStaleForDraft"
            placeholder="例如：我们只是熟人开玩笑，不需要当成高风险冲突；或者希望语气更直接一些..."
          ></textarea>
        </label>
        <div class="coach-feedback__actions">
          <button
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="submittingFeedback || isResultStaleForDraft || (!selectedFeedbackType && !feedbackNote.trim())"
            @click="handleSubmitAdjustment"
          >
            <Check :size="14" v-if="!submittingFeedback" />
            <Loader2 :size="14" v-else class="spin-icon" />
            <span>{{ submittingFeedback ? '提交中...' : '提交调整与反馈' }}</span>
          </button>
          <span v-if="adjustmentSubmitted" class="coach-feedback__tip">已记录反馈</span>
        </div>
      </details>
    </template>

    <div v-else class="report-empty coach-empty">
      <strong>{{ loading ? '正在分析这句话的语气和风险…' : '把准备发的话写进来，发之前先帮你看看' }}</strong>
    </div>
  </div>
</template>

<script setup>
import { Check, Copy, Loader2, Mic, RefreshCw, SlidersHorizontal, StopCircle } from 'lucide-vue-next'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { requestSceneReply } from '@/utils/requestSceneReply'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import {
  baselineMatchLabel,
  decisionFeedbackLabel,
  reactionShiftLabel as reactionShiftText,
  shouldShowReactionShift,
  translateInlineCodes,
} from '@/utils/displayText'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { resolveScopedPairId } from '@/utils/reportScopeSelection'
import { createRefreshAttemptGuard, parseRetryAfterSeconds } from '@/utils/refreshGuards'
import { AI_WAITING_NOTICE } from '@/utils/aiWaitFeedback'
import { createBackendRealtimeAsr, describeVoiceStartError, startBrowserSpeech } from '@/utils/realtimeVoice'
import { mergeVoiceTranscriptIntoDraft } from '@/utils/voiceDraft'
import { clearAllScopedDrafts, clearScopedDraft, loadScopedDraft, saveScopedDraft } from '@/utils/draftPersistence'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const draft = ref('')
const analyzedDraft = ref('')
const previousDraftBeforeExample = ref(null)
const result = ref(null)
const loading = ref(false)
const feedbackNote = ref('')
const copiedRewrite = ref(false)
let copyResetTimer = null
const voiceActive = ref(false)
const voiceStarting = ref(false)
const voiceFinalizing = ref(false)
const voiceStatus = ref('')
const voicePreview = ref('')
const voiceController = ref(null)
const simulationRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })
let voiceFallbackTried = false
let pageDisposed = false
let simulationRequestSeq = 0
let feedbackRequestSeq = 0
let voiceSessionSeq = 0
const scopedWorkspaces = new Map()

const refreshingRewrite = ref(false)
const customRewrite = ref('')
const rewriteVariantIndex = ref(0)
const currentSaferRewrite = computed(() => customRewrite.value || result.value?.safer_rewrite || '')
const isResultStaleForDraft = computed(() => {
  if (!result.value) return false
  return String(draft.value || '').trim() !== String(analyzedDraft.value || '').trim()
})
const adjustPanelOpen = ref(false)
const selectedFeedbackType = ref('')
const submittingFeedback = ref(false)
const adjustmentSubmitted = ref(false)

const feedbackOptions = [
  { value: 'judgement_too_high', label: decisionFeedbackLabel('judgement_too_high') },
  { value: 'judgement_too_low', label: decisionFeedbackLabel('judgement_too_low') },
  { value: 'direction_off', label: decisionFeedbackLabel('direction_off') },
  { value: 'copy_unnatural', label: decisionFeedbackLabel('copy_unnatural') },
  { value: 'acceptable', label: decisionFeedbackLabel('acceptable') },
]

const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const availablePairIds = computed(() =>
  (userStore.pairs || [])
    .filter((pair) => pair.status === 'active')
    .map((pair) => pair.id)
)
const pairId = computed(() =>
  resolveScopedPairId({
    preferredPairId: route.query.pair_id,
    fallbackPairId: userStore.activePairId,
    availablePairs: availablePairIds.value,
  }) || null
)
const accountScopeKey = computed(() => `${userStore.token || ''}::${userStore.me?.id || ''}`)
const workspaceScopeKey = computed(() => `${accountScopeKey.value}::${pairId.value || 'solo'}`)

const refreshButtonLabel = computed(() => (experienceMode.value.isDemoMode ? '刷新样例' : '重新看看'))
const analyzeButtonLabel = computed(() => (experienceMode.value.isDemoMode ? '查看这句样例' : '看看这句'))
const voiceButtonLabel = computed(() => {
  if (voiceFinalizing.value) return '整理中'
  if (voiceStarting.value) return '取消开启'
  if (voiceActive.value) return '停止'
  return '语音输入'
})
const alignmentButtonLabel = computed(() => {
  if (experienceMode.value.isDemoMode) return '看双视角样例'
  if (experienceMode.value.hasPairContext) return '看双方说法'
  return '看双视角'
})
const draftLength = computed(() => draft.value.trim().length)

const pressureRiskLevel = computed(() => {
  if (result.value?.rewrite_blocked) return 'high'
  const raw = String(result.value?.pressure_risk_level || '').trim().toLowerCase()
  if (raw) return raw
  const level = String(result.value?.risk_level || '').trim().toLowerCase()
  return level === 'high' || level === 'severe' ? 'watch' : 'none'
})

const pressureRiskLabel = computed(() => {
  if (result.value?.rewrite_blocked) return '存在明显施压或威胁风险'
  if (result.value?.pressure_risk_label) return result.value.pressure_risk_label
  if (pressureRiskLevel.value === 'high') return '存在明显施压或威胁风险'
  if (pressureRiskLevel.value === 'watch') return '略带催促语气，留意对方压迫感'
  return '暂无施压或威胁风险'
})

const escalationFrictionLevel = computed(() => {
  if (result.value?.rewrite_blocked) return 'high'
  if (result.value?.speaker_attribution === 'quoted_other_party') return 'low'
  const raw = String(result.value?.escalation_friction_level || '').trim().toLowerCase()
  if (raw) return raw
  const level = String(result.value?.risk_level || '').trim().toLowerCase()
  if (level === 'high' || level === 'severe') return 'high'
  if (level === 'medium') return 'medium'
  return 'low'
})

const escalationFrictionLabel = computed(() => {
  if (result.value?.escalation_friction_label) return result.value.escalation_friction_label
  if (result.value?.speaker_attribution === 'quoted_other_party') return '像是在转述对方的话，不是你主动发出的指责'
  if (escalationFrictionLevel.value === 'high') return '刺激性较强，容易引发明显对立'
  if (escalationFrictionLevel.value === 'medium') return '部分字眼容易让对方防御或让对话升级'
  return '表达较平和，未见明显刺激字眼'
})

const escalationCues = computed(() => {
  if (!Array.isArray(result.value?.escalation_cues)) return []
  return result.value.escalation_cues.filter((item) => typeof item === 'string' && item.trim())
})

const pressureRiskClass = computed(() => {
  if (pressureRiskLevel.value === 'high') return 'coach-risk-tone--high'
  if (pressureRiskLevel.value === 'watch') return 'coach-risk-tone--medium'
  return 'coach-risk-tone--low'
})

const frictionRiskClass = computed(() => {
  if (result.value?.speaker_attribution === 'quoted_other_party') return 'coach-risk-tone--low'
  if (escalationFrictionLevel.value === 'high') return 'coach-risk-tone--high'
  if (escalationFrictionLevel.value === 'medium') return 'coach-risk-tone--medium'
  return 'coach-risk-tone--low'
})

const riskLabel = computed(() => {
  if (!result.value) return '未评估'
  if (result.value.rewrite_blocked || result.value.risk_level === 'high' || result.value.risk_level === 'severe') {
    return '先别急着发'
  }
  if (result.value.speaker_attribution === 'quoted_other_party') {
    return '像在转述对方的话'
  }
  if (escalationFrictionLevel.value === 'high' || escalationFrictionLevel.value === 'medium' || result.value.risk_level === 'medium') {
    return '留意措辞摩擦'
  }
  return '表达较平和'
})

const riskClass = computed(() => {
  if (result.value?.rewrite_blocked || result.value?.risk_level === 'high' || result.value?.risk_level === 'severe') {
    return 'coach-risk--high'
  }
  if (escalationFrictionLevel.value === 'high' || escalationFrictionLevel.value === 'medium' || result.value?.risk_level === 'medium') {
    return 'coach-risk--medium'
  }
  return 'coach-risk--low'
})

const baselineLabel = computed(() => baselineMatchLabel(result.value?.baseline_match))
const reactionShiftLabel = computed(() => reactionShiftText(result.value?.reaction_shift))
const showReactionShiftPill = computed(() => shouldShowReactionShift(result.value))
const displayDeviationReasons = computed(() =>
  (result.value?.deviation_reasons || []).map(translateInlineCodes)
)

const confidenceLabel = computed(() => {
  const value = Number(result.value?.confidence)
  if (!Number.isFinite(value)) return '还没有结果'
  if (value >= 0.8) return `把握度 ${value.toFixed(2)} · 比较稳`
  if (value >= 0.6) return `把握度 ${value.toFixed(2)} · 还可以`
  return `把握度 ${value.toFixed(2)} · 先当提醒`
})

function snapshotWorkspaceState() {
  return {
    draft: draft.value,
    analyzedDraft: analyzedDraft.value,
    result: result.value,
    customRewrite: customRewrite.value,
    feedbackNote: feedbackNote.value,
    selectedFeedbackType: selectedFeedbackType.value,
    adjustmentSubmitted: adjustmentSubmitted.value,
    adjustPanelOpen: adjustPanelOpen.value,
  }
}

function applyWorkspaceState(saved = null) {
  draft.value = saved?.draft ?? ''
  analyzedDraft.value = saved?.analyzedDraft ?? ''
  previousDraftBeforeExample.value = null
  result.value = saved?.result ?? null
  customRewrite.value = saved?.customRewrite ?? ''
  feedbackNote.value = saved?.feedbackNote ?? ''
  selectedFeedbackType.value = saved?.selectedFeedbackType ?? ''
  adjustmentSubmitted.value = Boolean(saved?.adjustmentSubmitted)
  adjustPanelOpen.value = Boolean(saved?.adjustPanelOpen)
}

function buildDraftStorageParams(scopePairId = pairId.value) {
  return {
    surface: 'message_simulation',
    ownerId: userStore.me?.id || '',
    token: userStore.token || '',
    scopeId: scopePairId || 'solo',
  }
}

function saveWorkspaceToSession(targetScopePairId = pairId.value, snapshot = snapshotWorkspaceState()) {
  if (experienceMode.value.isDemoMode) return
  saveScopedDraft({
    ...buildDraftStorageParams(targetScopePairId),
    value: {
      draft: snapshot.draft,
      analyzedDraft: snapshot.analyzedDraft,
      result: snapshot.result,
      customRewrite: snapshot.customRewrite,
    },
  })
}

function loadWorkspaceFromSession(targetScopePairId = pairId.value) {
  if (experienceMode.value.isDemoMode) return null
  return loadScopedDraft(buildDraftStorageParams(targetScopePairId))
}

function persistCurrentWorkspace(targetKey = workspaceScopeKey.value, targetScopePairId = pairId.value) {
  const snapshot = snapshotWorkspaceState()
  scopedWorkspaces.set(targetKey, snapshot)
  saveWorkspaceToSession(targetScopePairId, snapshot)
}

function clearDraftWorkspace() {
  applyWorkspaceState(null)
  scopedWorkspaces.delete(workspaceScopeKey.value)
  clearScopedDraft(buildDraftStorageParams(pairId.value))
}

watch(
  () => draft.value,
  () => {
    if (pageDisposed || experienceMode.value.isDemoMode) return
    persistCurrentWorkspace(workspaceScopeKey.value, pairId.value)
  }
)

onMounted(() => {
  if (experienceMode.value.isDemoMode) {
    draft.value = demoFixture.messageSimulation.draft
    loadPreview()
    return
  }
  const saved = scopedWorkspaces.get(workspaceScopeKey.value) || loadWorkspaceFromSession(pairId.value)
  if (saved) {
    applyWorkspaceState(saved)
  }
})

onBeforeUnmount(() => {
  if (!experienceMode.value.isDemoMode) {
    persistCurrentWorkspace(workspaceScopeKey.value, pairId.value)
  }
  pageDisposed = true
  simulationRequestSeq++
  feedbackRequestSeq++
  if (copyResetTimer) clearTimeout(copyResetTimer)
  invalidateVoiceSession()
})

watch(
  () => accountScopeKey.value,
  (nextAccount, previousAccount) => {
    if (nextAccount === previousAccount) return
    const [prevToken, prevUserId] = String(previousAccount || '').split('::')
    const [nextToken, nextUserId] = String(nextAccount || '').split('::')
    const hydratedSameSession = Boolean(nextToken && nextToken === prevToken && !prevUserId && nextUserId)
    if (hydratedSameSession) {
      if (!draft.value && !result.value) {
        const restored = loadWorkspaceFromSession(pairId.value)
        if (restored) applyWorkspaceState(restored)
      }
      return
    }
    simulationRequestSeq++
    feedbackRequestSeq++
    loading.value = false
    refreshingRewrite.value = false
    submittingFeedback.value = false
    scopedWorkspaces.clear()
    clearAllScopedDrafts()
    invalidateVoiceSession()
    applyWorkspaceState(null)
  },
  { flush: 'sync' }
)

watch(
  () => workspaceScopeKey.value,
  (nextScopeKey, previousScopeKey) => {
    if (nextScopeKey === previousScopeKey) return
    if (previousScopeKey && previousScopeKey.startsWith(`${accountScopeKey.value}::`)) {
      const prevPairSegment = previousScopeKey.slice(`${accountScopeKey.value}::`.length) || 'solo'
      persistCurrentWorkspace(previousScopeKey, prevPairSegment === 'solo' ? '' : prevPairSegment)
    }
    simulationRequestSeq++
    feedbackRequestSeq++
    loading.value = false
    refreshingRewrite.value = false
    submittingFeedback.value = false
    invalidateVoiceSession()

    const saved = scopedWorkspaces.get(nextScopeKey) || loadWorkspaceFromSession(pairId.value)
    if (saved) {
      applyWorkspaceState(saved)
    } else if (experienceMode.value.isDemoMode) {
      applyWorkspaceState({
        draft: demoFixture.messageSimulation.draft,
        analyzedDraft: demoFixture.messageSimulation.draft.trim(),
        result: cloneDemo(demoFixture.messageSimulation),
      })
    } else {
      applyWorkspaceState(null)
    }
  },
  { flush: 'sync' }
)

async function loadPreview(forceCall = false) {
  const requestSeq = ++simulationRequestSeq
  const requestScopeKey = workspaceScopeKey.value
  const requestPairId = pairId.value
  const submittedDraft = draft.value
  const isCurrentRequest = () => (
    !pageDisposed
    && requestSeq === simulationRequestSeq
    && workspaceScopeKey.value === requestScopeKey
    && draft.value === submittedDraft
  )

  if (experienceMode.value.isDemoMode && !forceCall) {
    const demoDraft = String(draft.value || demoFixture.messageSimulation.draft).trim()
    result.value = cloneDemo(demoFixture.messageSimulation)
    if (!draft.value) draft.value = demoFixture.messageSimulation.draft
    analyzedDraft.value = demoDraft
    customRewrite.value = ''
    feedbackNote.value = ''
    selectedFeedbackType.value = ''
    adjustmentSubmitted.value = false
    persistCurrentWorkspace(requestScopeKey)
    return
  }

  const normalizedDraft = String(submittedDraft || '').trim()
  if (!normalizedDraft) {
    showToast('先输入原句')
    return
  }

  previousDraftBeforeExample.value = null
  loading.value = true
  customRewrite.value = ''
  adjustmentSubmitted.value = false
  selectedFeedbackType.value = ''
  try {
    const simulation = await api.simulateMessage(requestPairId, normalizedDraft)
    if (!isCurrentRequest()) return
    result.value = simulation
    analyzedDraft.value = normalizedDraft
    feedbackNote.value = ''
    persistCurrentWorkspace(requestScopeKey)
  } catch (e) {
    if (!isCurrentRequest()) return
    if (e?.statusCode === 429) {
      simulationRefreshGuard.setCooldown(parseRetryAfterSeconds(e.message))
    }
    showToast(e.message || '这次没分析出来，请稍后再试')
  } finally {
    if (!pageDisposed && requestSeq === simulationRequestSeq) {
      loading.value = false
    }
  }
}

function consumeSimulationCooldown() {
  if (experienceMode.value.isDemoMode) return true
  const remainingSeconds = simulationRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`看得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return false
  }
  simulationRefreshGuard.markRun()
  return true
}

function handleRefreshPreview() {
  return runSimulation()
}

function isCurrentVoiceSession(sessionSeq, startedScopeKey) {
  return (
    !pageDisposed
    && sessionSeq === voiceSessionSeq
    && workspaceScopeKey.value === startedScopeKey
  )
}

function cleanupVoiceState(status = '', { keepPreview = false } = {}) {
  voiceActive.value = false
  voiceStarting.value = false
  voiceFinalizing.value = false
  voiceStatus.value = status
  if (!keepPreview) voicePreview.value = ''
  voiceController.value = null
}

function invalidateVoiceSession(status = '', options = {}) {
  voiceSessionSeq += 1
  const controller = voiceController.value
  cleanupVoiceState(status, options)
  controller?.cleanup?.()
}

function stopVoiceInput({ discard = false } = {}) {
  if (!voiceController.value) {
    invalidateVoiceSession()
    return
  }
  if (discard) {
    invalidateVoiceSession()
    return
  }
  voiceActive.value = false
  voiceStarting.value = false
  voiceFinalizing.value = true
  voiceStatus.value = '正在整理最后一句。'
  voiceController.value.stop?.({ discard: false })
}

function startBrowserVoice(reason = '', sessionSeq = voiceSessionSeq, startedScopeKey = workspaceScopeKey.value) {
  if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
  const controller = startBrowserSpeech({
    reason,
    onActive: () => {
      if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) {
        controller.cleanup()
        return
      }
      voiceStarting.value = false
      voiceActive.value = true
      voiceFinalizing.value = false
    },
    onStatus: (text) => {
      if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
      voiceStatus.value = text
    },
    onPartial: (text) => {
      if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
      if (!voiceActive.value || voiceFinalizing.value) return
      voicePreview.value = text
    },
    onFinal: (payload) => handleVoiceFinal(payload, sessionSeq, startedScopeKey),
    onError: (message) => {
      if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
      cleanupVoiceState()
      showToast(message || '这次没识别出来，请重试')
    },
  })
  if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) {
    controller.cleanup()
    return
  }
  voiceController.value = controller
}

function handleBackendVoiceError(message, sessionSeq, startedScopeKey) {
  if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
  cleanupVoiceState()
  if (!voiceFallbackTried) {
    voiceFallbackTried = true
    try {
      startBrowserVoice(message, sessionSeq, startedScopeKey)
      return
    } catch {
      // Fall through to show the backend error message.
    }
  }
  showToast(message || '这次没识别出来，请重试')
}

async function handleVoiceFinal(payload, sessionSeq, startedScopeKey) {
  if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
  const text = String(payload?.text || payload || voicePreview.value || '').trim()
  cleanupVoiceState(text ? '转写完成。' : '录音结束。')
  if (!text) {
    showToast('这段录音没有整理出稳定文字，请再试一次')
    return
  }
  draft.value = mergeVoiceTranscriptIntoDraft(draft.value, text)
  persistCurrentWorkspace(startedScopeKey)
  showToast('语音已填入原句')
}

async function toggleVoiceInput() {
  if (voiceActive.value) {
    stopVoiceInput()
    return
  }
  if (voiceStarting.value) {
    invalidateVoiceSession('已取消开启麦克风。')
    return
  }
  if (voiceFinalizing.value) {
    showToast('正在整理最后一句')
    return
  }
  if (!experienceMode.value.canUseVoice) {
    showToast(featureUnavailableReason('voice', experienceMode.value))
    return
  }
  const sessionSeq = ++voiceSessionSeq
  const startedScopeKey = workspaceScopeKey.value
  let controller = null
  try {
    voiceFallbackTried = false
    voiceStarting.value = true
    voiceStatus.value = '正在打开麦克风。'
    voicePreview.value = ''
    controller = createBackendRealtimeAsr({
      getSocketUrl: () => api.buildRealtimeAsrSocketUrl(),
      onActive: () => {
        if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) {
          controller?.cleanup?.()
          return
        }
        voiceStarting.value = false
        voiceActive.value = true
        voiceFinalizing.value = false
      },
      onStatus: (text) => {
        if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
        voiceStatus.value = text
      },
      onPartial: (text) => {
        if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
        if (!voiceActive.value || voiceFinalizing.value) return
        voicePreview.value = text
        voiceStatus.value = '正在把语音转成文字。'
      },
      onFinal: (payload) => handleVoiceFinal(payload, sessionSeq, startedScopeKey),
      onError: (message) => handleBackendVoiceError(message, sessionSeq, startedScopeKey),
    })
    voiceController.value = controller
    const started = await controller.start()
    if (!started || !isCurrentVoiceSession(sessionSeq, startedScopeKey)) {
      controller.cleanup()
      if (voiceController.value === controller) cleanupVoiceState()
      return
    }
  } catch (error) {
    controller?.cleanup?.()
    if (!isCurrentVoiceSession(sessionSeq, startedScopeKey)) return
    try {
      startBrowserVoice(error.message, sessionSeq, startedScopeKey)
    } catch (fallbackError) {
      cleanupVoiceState()
      showToast(describeVoiceStartError(fallbackError) || describeVoiceStartError(error))
    }
  }
}

function applyQuickDraft(text) {
  const current = draft.value
  if (current.trim() && current !== text && previousDraftBeforeExample.value === null) {
    previousDraftBeforeExample.value = current
  }
  draft.value = text
  showToast('已填入示例句，点“看看这句”再开始分析')
}

function undoQuickDraft() {
  if (previousDraftBeforeExample.value === null) return
  draft.value = previousDraftBeforeExample.value
  previousDraftBeforeExample.value = null
  showToast('已恢复原草稿')
}

async function runSimulation() {
  if (!draft.value.trim()) {
    showToast('先输入原句')
    return
  }
  if (!consumeSimulationCooldown()) return
  showToast(AI_WAITING_NOTICE)
  await loadPreview(true)
}

async function handleRefreshRewrite() {
  if (
    result.value?.rewrite_blocked
    || isResultStaleForDraft.value
    || refreshingRewrite.value
    || loading.value
    || !analyzedDraft.value.trim()
  ) {
    if (isResultStaleForDraft.value) {
      showToast('原句已修改，请先点“看看这句”重新分析后再改写')
    }
    return
  }
  const targetDraft = analyzedDraft.value.trim()
  const requestScopeKey = workspaceScopeKey.value
  const requestResult = result.value
  const requestSeq = simulationRequestSeq
  const current = () => (
    !pageDisposed
    && requestSeq === simulationRequestSeq
    && workspaceScopeKey.value === requestScopeKey
    && result.value === requestResult
    && !isResultStaleForDraft.value
    && String(analyzedDraft.value || '').trim() === targetDraft
  )
  refreshingRewrite.value = true
  try {
    const reply = await requestSceneReply(
      api,
      pairId.value,
      {
        sourceLabel: '发前看看',
        summary: `原句：${targetDraft}\n上一版：${currentSaferRewrite.value}`,
      },
      '换一种日常说话的表达，保留原话里的事实、感受、要求和边界。不编造对方的处境，不强加撒娇或示弱的语气，不保证对方会如何回应。只返回改写后的消息。',
      current
    )
    if (current()) {
      customRewrite.value = reply
      persistCurrentWorkspace(requestScopeKey)
    }
  } catch (error) {
    if (current()) showToast(error.message || '这次没改出来，请重试。')
  } finally {
    if (!pageDisposed && requestSeq === simulationRequestSeq) {
      refreshingRewrite.value = false
    }
  }
}

async function copyRewrite() {
  if (isResultStaleForDraft.value || result.value?.rewrite_blocked) return
  const text = String(currentSaferRewrite.value || '').trim()
  if (!text) return
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copiedRewrite.value = true
    if (copyResetTimer) clearTimeout(copyResetTimer)
    copyResetTimer = setTimeout(() => { copiedRewrite.value = false }, 2200)
    showToast('已复制改写后的句子')
  } catch {
    showToast('复制没成功，请手动选中复制')
  }
}

function sendRewriteToChat() {
  if (isResultStaleForDraft.value || result.value?.rewrite_blocked) return
  const text = String(currentSaferRewrite.value || '').trim()
  if (!text) return
  router.push({
    path: '/chat',
    query: {
      prompt: `我打算这样跟对方说：“${text}”。你帮我看看还有没有更自然或更贴合当前处境的表达？`,
    },
  })
}

async function handleSubmitAdjustment() {
  if (submittingFeedback.value || isResultStaleForDraft.value) return
  if (!selectedFeedbackType.value && !feedbackNote.value.trim()) {
    showToast('请选择反馈类型或输入调整说明')
    return
  }
  const requestSeq = ++feedbackRequestSeq
  const requestScopeKey = workspaceScopeKey.value
  const isCurrentFeedback = () => (
    !pageDisposed
    && requestSeq === feedbackRequestSeq
    && workspaceScopeKey.value === requestScopeKey
  )
  submittingFeedback.value = true
  try {
    const feedbackType = selectedFeedbackType.value || 'somewhat_accurate'
    if (experienceMode.value.isDemoMode) {
      if (!isCurrentFeedback()) return
      adjustmentSubmitted.value = true
      persistCurrentWorkspace(requestScopeKey)
      showToast('已记下本次样例反馈')
      return
    }
    const eventId = result.value?.event_id
    if (!eventId) throw new Error('这条结果暂时不能提交反馈。')
    await api.submitDecisionFeedback(eventId, feedbackType, feedbackNote.value.trim())
    if (!isCurrentFeedback()) return
    adjustmentSubmitted.value = true
    persistCurrentWorkspace(requestScopeKey)
    showToast('已记录反馈')
  } catch (e) {
    if (isCurrentFeedback()) {
      showToast(e.message || '调整提交失败，请重试')
    }
  } finally {
    if (!pageDisposed && requestSeq === feedbackRequestSeq) {
      submittingFeedback.value = false
    }
  }
}
</script>

<style scoped>
.coach-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 32px;
  display: grid;
  gap: 16px;
}

.coach-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.coach-head__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.coach-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  background:
    radial-gradient(circle at top right, rgba(240, 213, 184, 0.24), transparent 26%),
    rgba(255, 251, 247, 0.9);
}

.coach-input__main {
  display: grid;
  gap: 12px;
}

.coach-quick-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 2px 0 4px;
}

.coach-quick-chips__hint {
  font-size: 13px;
  color: var(--text-muted, #7c7267);
}

.coach-quick-chip {
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 999px;
  border: 1px solid rgba(199, 131, 84, 0.22);
  background: rgba(255, 255, 255, 0.85);
  color: #794e24;
  cursor: pointer;
  transition: all 0.18s ease;
}

.coach-quick-chip:hover {
  background: #fff4ea;
  border-color: rgba(199, 131, 84, 0.45);
  color: #633c16;
  transform: translateY(-1px);
}

.coach-quick-chip--undo {
  border-color: rgba(23, 56, 94, 0.24);
  background: rgba(238, 246, 250, 0.9);
  color: #17385e;
  font-weight: 700;
}

.coach-quick-chip--undo:hover {
  background: rgba(226, 239, 247, 0.96);
  border-color: rgba(23, 56, 94, 0.42);
  color: #102a47;
}

.coach-stale-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  border: 1px solid rgba(189, 134, 53, 0.36);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 246, 229, 0.94), rgba(255, 251, 244, 0.96));
  color: #5b3b14;
}

.coach-stale-banner__text {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.coach-stale-banner__text strong {
  font-size: 14px;
  font-weight: 800;
  color: #7c4a12;
}

.coach-stale-banner__text p {
  font-size: 13px;
  line-height: 1.55;
  color: rgba(91, 59, 20, 0.88);
}

.coach-results--stale,
.coach-results--stale ~ .coach-feedback {
  opacity: 0.62;
  transition: opacity 0.18s ease;
}

.coach-input__textarea {
  min-height: 170px;
  font-family: var(--font-serif);
  font-size: 17px;
  line-height: 1.85;
  background: rgba(255, 254, 251, 0.94);
}

.coach-voice-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
}

.coach-voice-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  color: rgba(74, 83, 91, 0.78);
  font-size: 13px;
  line-height: 1.5;
}

.coach-voice-status p {
  min-width: 0;
  max-height: 6em;
  overflow: hidden;
  overflow-y: auto;
  overflow-wrap: anywhere;
  text-overflow: ellipsis;
  white-space: normal;
}

.coach-voice-dot,
.coach-voice-pulse {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #7b8c6d;
}

.coach-voice-pulse {
  box-shadow: 0 0 0 5px rgba(123, 140, 109, 0.14);
}

.coach-voice-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 38px;
  flex: 0 0 auto;
  padding: 0 12px;
  border: 1px solid rgba(56, 42, 30, 0.1);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  color: #17385e;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.coach-voice-button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.coach-voice-button--active {
  border-color: rgba(189, 75, 53, 0.22);
  background: rgba(243, 216, 208, 0.58);
  color: #8a3524;
}

.coach-input__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: rgba(92, 101, 109, 0.74);
  font-size: 12px;
  font-weight: 700;
}

.coach-privacy-note {
  color: rgba(74, 83, 91, 0.8);
  font-weight: 600;
}

.coach-input__footer-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.coach-clear-draft {
  padding: 2px 9px;
  border: 1px solid rgba(56, 42, 30, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  color: #5b5248;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.coach-clear-draft:hover {
  background: #fff4ea;
  border-color: rgba(199, 131, 84, 0.36);
  color: #633c16;
}

.coach-risk-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
  margin-bottom: 10px;
}

.coach-risk-split__item {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid rgba(56, 42, 30, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.coach-risk-split__label {
  font-size: 11px;
  font-weight: 700;
  color: rgba(92, 101, 109, 0.78);
}

.coach-risk-split__item strong {
  font-size: 13px;
  line-height: 1.45;
  font-weight: 700;
}

.coach-risk-tone--low {
  color: #2f5b6b;
}

.coach-risk-tone--medium {
  color: #935b14;
}

.coach-risk-tone--high {
  color: #9c3825;
}

.coach-escalation-cues {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding-left: 18px;
  color: #7c4a12;
  font-size: 13px;
  line-height: 1.6;
}

.coach-feedback__note {
  color: rgba(108, 99, 89, 0.68);
  font-size: 12px;
  font-weight: 700;
}

.coach-results {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.coach-result-card h3,
.coach-risk-card h3,
.coach-rewrite-card h3 {
  margin-top: 4px;
  color: #17385e;
  font-family: var(--font-serif);
  font-size: 22px;
  line-height: 1.45;
}

.coach-result-card p:last-child,
.coach-risk-card p:last-child {
  margin-top: 10px;
  color: rgba(92, 101, 109, 0.78);
  line-height: 1.76;
}

.coach-risk-card {
  background: rgba(255, 252, 247, 0.94);
}

.coach-risk-card__meta,
.coach-inline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.coach-risk-card__meta span,
.coach-inline-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(56, 42, 30, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: rgba(74, 83, 91, 0.82);
  font-size: 12px;
  font-weight: 700;
}

.coach-risk--low {
  border-color: rgba(67, 98, 115, 0.2);
  background: linear-gradient(180deg, rgba(238, 246, 250, 0.62), rgba(255, 251, 247, 0.88));
}

.coach-risk--medium {
  border-color: rgba(189, 134, 53, 0.24);
  background: linear-gradient(180deg, rgba(244, 233, 209, 0.54), rgba(255, 251, 247, 0.88));
}

.coach-risk--high {
  border-color: rgba(189, 75, 53, 0.28);
  background: linear-gradient(180deg, rgba(243, 216, 208, 0.56), rgba(255, 251, 247, 0.88));
}

.coach-rewrite-card {
  grid-column: 1 / -1;
}

.coach-rewrite-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.coach-rewrite-card blockquote {
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.74);
  color: #17385e;
  font-family: var(--font-serif);
  font-size: 22px;
  line-height: 1.65;
}

.coach-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.coach-actions__column {
  padding: 4px 2px 2px;
}

.coach-actions__column--muted {
  border-left: 1px solid rgba(56, 42, 30, 0.08);
  padding-left: 18px;
}

.plain-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  padding-left: 18px;
  color: rgba(74, 83, 91, 0.82);
  line-height: 1.74;
}

.coach-secondary {
  background: rgba(255, 252, 247, 0.82);
}

.coach-feedback {
  background: rgba(255, 252, 247, 0.76);
}

.coach-feedback summary {
  list-style: none;
  color: #17385e;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.coach-feedback summary::-webkit-details-marker {
  display: none;
}

.coach-feedback[open] summary {
  margin-bottom: 12px;
}

.feedback-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.feedback-row .btn.active {
  background: var(--brand-primary, #d97706);
  color: #fff;
  border-color: var(--brand-primary, #d97706);
}

.coach-feedback__desc {
  font-size: 13px;
  color: rgba(74, 83, 91, 0.78);
  margin-bottom: 10px;
}

.coach-feedback__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.coach-feedback__tip {
  font-size: 13px;
  color: #10b981;
  font-weight: 500;
}

.btn-adjust-judgment {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #64748b;
  font-size: 12px;
  padding: 3px 8px;
}

.btn-regenerate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-size: 13px;
  padding: 4px 10px;
}

.btn-regenerate:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.08);
}

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.coach-empty {
  min-height: 220px;
}

@media (max-width: 900px) {
  .coach-input,
  .coach-results,
  .coach-actions {
    grid-template-columns: 1fr;
  }

  .coach-actions__column--muted {
    border-left: 0;
    border-top: 1px solid rgba(56, 42, 30, 0.08);
    padding-left: 2px;
    padding-top: 18px;
  }
}

@media (max-width: 760px) {
  .coach-page {
    width: min(100% - 20px, var(--content-max));
  }

  .coach-head {
    display: grid;
  }

  .coach-voice-row {
    align-items: stretch;
    flex-direction: column;
  }

  .coach-voice-status p {
    white-space: normal;
  }

  .coach-voice-button {
    width: 100%;
  }

  .coach-stale-banner {
    align-items: stretch;
    flex-direction: column;
  }

  .coach-risk-split {
    grid-template-columns: 1fr;
  }
}
</style>

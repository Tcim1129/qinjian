<template>
  <div class="coach-page">
    <div class="page-head coach-head">
      <div>
        <p class="eyebrow">发前看看</p>
        <h2>输入一句原话，直接看风险和改写</h2>
      </div>
      <div class="coach-head__actions">
        <button class="btn btn-ghost btn-sm" :disabled="loading" @click="handleRefreshPreview">{{ refreshButtonLabel }}</button>
        <button class="btn btn-primary btn-sm" @click="$router.push('/alignment')">{{ alignmentButtonLabel }}</button>
      </div>
    </div>

    <section class="coach-input card">
      <div class="coach-input__main">
        <div class="card-header">
          <div>
            <p class="eyebrow">准备发的话</p>
            <h3>把最想发的那句话先贴在这儿~</h3>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="loading" @click="runSimulation">
            {{ loading ? '查看中...' : analyzeButtonLabel }}
          </button>
        </div>

        <div class="coach-quick-chips">
          <span class="coach-quick-chips__hint">试试高情商化解：</span>
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
        </div>

        <label class="field">
          <span>原句</span>
          <textarea
            v-model="draft"
            class="input input-textarea coach-input__textarea"
            rows="5"
            placeholder="把你在气头上、或者犹豫要不要发的那句话贴进来，智能体帮你一键化解火药味，把‘怨气’变成‘让人心软的高情商表达’~ 比如：'你今天怎么又这么晚才回我，我真的很烦。'"
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
            :class="{ 'coach-voice-button--active': voiceActive || voiceFinalizing }"
            :disabled="loading || voiceFinalizing"
            :aria-label="voiceActive || voiceFinalizing ? '停止转写' : '语音转文字'"
            :title="voiceActive || voiceFinalizing ? '停止转写' : '语音转文字'"
            @click="toggleVoiceInput"
          >
            <Loader2 v-if="voiceFinalizing" :size="17" class="spin-icon" />
            <StopCircle v-else-if="voiceActive" :size="18" />
            <Mic v-else :size="18" />
            <span>{{ voiceButtonLabel }}</span>
          </button>
        </div>

        <div class="coach-input__footer">
          <span>{{ draftLength ? `已输入 ${draftLength} 字` : '把心里那句纠结的话写下来，先不着急点发送~' }}</span>
        </div>
      </div>
    </section>

    <template v-if="result">
      <section class="coach-results">
        <article class="card card-accent coach-risk-card" :class="riskClass">
          <div class="card-header">
            <div>
              <p class="eyebrow">风险判断</p>
              <h3>{{ riskLabel }}</h3>
            </div>
            <button
              class="btn btn-ghost btn-xs btn-adjust-judgment"
              type="button"
              @click="adjustPanelOpen = !adjustPanelOpen"
            >
              <SlidersHorizontal :size="13" />
              <span>{{ adjustPanelOpen ? '收起调整' : '调整判断' }}</span>
            </button>
          </div>
          <p>{{ result.risk_reason }}</p>
          <div class="coach-risk-card__meta">
            <span>{{ baselineLabel }}</span>
            <span>{{ reactionShiftLabel }}</span>
          </div>
        </article>

        <article class="card coach-result-card">
          <p class="eyebrow">对方可能先听成</p>
          <h3>{{ result.partner_view }}</h3>
          <p>{{ result.likely_impact }}</p>
        </article>

        <article class="card coach-rewrite-card">
          <div class="card-header">
            <div>
              <p class="eyebrow">推荐改写</p>
              <h3>推荐这样改</h3>
            </div>
            <button
              class="btn btn-ghost btn-sm btn-regenerate"
              type="button"
              :disabled="refreshingRewrite || loading"
              @click="handleRefreshRewrite"
              title="换一种表达思路"
            >
              <RefreshCw :size="14" :class="{ 'is-spinning': refreshingRewrite }" />
              <span>{{ refreshingRewrite ? '构思中...' : '换个改法' }}</span>
            </button>
          </div>
          <blockquote>{{ currentSaferRewrite }}</blockquote>
          <div class="coach-inline-meta">
            <span>{{ result.conversation_goal }}</span>
            <span>{{ result.suggested_tone }}</span>
            <span>{{ confidenceLabel }}</span>
          </div>
        </article>
      </section>

      <section class="coach-actions card">
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

      <section v-if="displayDeviationReasons.length" class="coach-secondary card">
        <p class="eyebrow">为什么会偏离</p>
        <ul class="plain-list">
          <li v-for="item in displayDeviationReasons" :key="item">{{ item }}</li>
        </ul>
      </section>

      <details class="coach-feedback card" :open="adjustPanelOpen || Boolean(feedbackNote)">
        <summary @click="adjustPanelOpen = !adjustPanelOpen">调整系统判断与反馈</summary>
        <p class="coach-feedback__desc">如果觉得系统判断的风险偏高、或理解与实际情况不符，请在此修正并提交：</p>
        <div class="feedback-row">
          <button
            v-for="option in feedbackOptions"
            :key="option.value"
            type="button"
            class="btn btn-ghost btn-sm"
            :class="{ active: selectedFeedbackType === option.value }"
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
            placeholder="例如：我们只是熟人开玩笑，不需要当成高风险冲突；或者希望语气更直接一些..."
          ></textarea>
        </label>
        <div class="coach-feedback__actions">
          <button
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="submittingFeedback || (!selectedFeedbackType && !feedbackNote.trim())"
            @click="handleSubmitAdjustment"
          >
            <Check :size="14" v-if="!submittingFeedback" />
            <Loader2 :size="14" v-else class="spin-icon" />
            <span>{{ submittingFeedback ? '提交中...' : '提交调整与反馈' }}</span>
          </button>
          <span v-if="adjustmentSubmitted" class="coach-feedback__tip">✓ 已记录反馈</span>
        </div>
      </details>
    </template>

    <div v-else class="report-empty coach-empty">
      <strong>{{ loading ? '正在悄悄帮你斟酌语句中…' : '把最想说的那句话放进来，我们先帮你把把关~' }}</strong>
    </div>
  </div>
</template>

<script setup>
import { Check, Loader2, Mic, RefreshCw, SlidersHorizontal, StopCircle } from 'lucide-vue-next'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { requestSceneReply } from '@/utils/requestSceneReply'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import {
  baselineMatchLabel,
  decisionFeedbackLabel,
  reactionShiftLabel as reactionShiftText,
  translateInlineCodes,
} from '@/utils/displayText'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { resolveScopedPairId } from '@/utils/reportScopeSelection'
import { createRefreshAttemptGuard, parseRetryAfterSeconds } from '@/utils/refreshGuards'
import { AI_WAITING_NOTICE } from '@/utils/aiWaitFeedback'
import { createBackendRealtimeAsr, describeVoiceStartError, startBrowserSpeech } from '@/utils/realtimeVoice'
import { mergeVoiceTranscriptIntoDraft } from '@/utils/voiceDraft'

const route = useRoute()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const draft = ref('')
const result = ref(null)
const loading = ref(false)
const feedbackNote = ref('')
const voiceActive = ref(false)
const voiceFinalizing = ref(false)
const voiceStatus = ref('')
const voicePreview = ref('')
const voiceController = ref(null)
const simulationRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })
let voiceFallbackTried = false
let pageDisposed = false

const refreshingRewrite = ref(false)
const customRewrite = ref('')
const rewriteVariantIndex = ref(0)
const currentSaferRewrite = computed(() => customRewrite.value || result.value?.safer_rewrite || '')
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

const refreshButtonLabel = computed(() => (experienceMode.value.isDemoMode ? '刷新样例' : '重新看看'))
const analyzeButtonLabel = computed(() => (experienceMode.value.isDemoMode ? '查看这句样例' : '看看这句'))
const voiceButtonLabel = computed(() => {
  if (voiceFinalizing.value) return '整理中'
  if (voiceActive.value) return '停止'
  return '语音输入'
})
const alignmentButtonLabel = computed(() => {
  if (experienceMode.value.isDemoMode) return '看双视角样例'
  if (experienceMode.value.hasPairContext) return '看双方说法'
  return '看双视角'
})
const draftLength = computed(() => draft.value.trim().length)

const riskLabel = computed(() => {
  const map = { low: '比较稳', medium: '需要留意', high: '先别急着发', severe: '先别急着发' }
  return map[result.value?.risk_level] || '未评估'
})

const riskClass = computed(() => {
  const level = result.value?.risk_level
  if (level === 'high' || level === 'severe') return 'coach-risk--high'
  if (level === 'medium') return 'coach-risk--medium'
  return 'coach-risk--low'
})

const baselineLabel = computed(() => baselineMatchLabel(result.value?.baseline_match))
const reactionShiftLabel = computed(() => reactionShiftText(result.value?.reaction_shift))
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

onMounted(() => {
  if (experienceMode.value.isDemoMode) {
    draft.value = demoFixture.messageSimulation.draft
    loadPreview()
  }
})

onBeforeUnmount(() => {
  pageDisposed = true
  voiceController.value?.cleanup?.()
  cleanupVoiceState()
})

watch(
  () => pairId.value,
  (nextPairId, previousPairId) => {
    if (experienceMode.value.isDemoMode) return
    if (nextPairId === previousPairId) return
    if (!draft.value.trim() && !result.value) return
    void loadPreview()
  }
)

async function loadPreview(forceCall = false) {
  loading.value = true
  customRewrite.value = ''
  adjustmentSubmitted.value = false
  selectedFeedbackType.value = ''
  try {
    if (experienceMode.value.isDemoMode && !forceCall) {
      result.value = cloneDemo(demoFixture.messageSimulation)
      if (!draft.value) draft.value = demoFixture.messageSimulation.draft
      feedbackNote.value = ''
      return
    }
    const simulation = await api.simulateMessage(pairId.value, draft.value || demoFixture.messageSimulation.draft)
    result.value = simulation
    feedbackNote.value = ''
  } catch (e) {
    if (e?.statusCode === 429) {
      simulationRefreshGuard.setCooldown(parseRetryAfterSeconds(e.message))
    }
    result.value = null
    showToast(e.message || '这次没分析出来，请稍后再试')
  } finally {
    loading.value = false
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

function cleanupVoiceState(status = '', { keepPreview = false } = {}) {
  voiceActive.value = false
  voiceFinalizing.value = false
  voiceStatus.value = status
  if (!keepPreview) voicePreview.value = ''
  voiceController.value = null
}

function stopVoiceInput({ discard = false } = {}) {
  if (!voiceController.value) {
    cleanupVoiceState()
    return
  }
  voiceActive.value = false
  voiceFinalizing.value = !discard
  voiceStatus.value = discard ? '' : '正在整理最后一句。'
  voiceController.value.stop?.({ discard: Boolean(discard) })
  if (discard) cleanupVoiceState()
}

function startBrowserVoice(reason = '') {
  voiceController.value = startBrowserSpeech({
    reason,
    onActive: () => {
      voiceActive.value = true
      voiceFinalizing.value = false
    },
    onStatus: (text) => {
      voiceStatus.value = text
    },
    onPartial: (text) => {
      if (!voiceActive.value || voiceFinalizing.value) return
      voicePreview.value = text
    },
    onFinal: handleVoiceFinal,
    onError: (message) => {
      cleanupVoiceState()
      showToast(message || '这次没识别出来，请重试')
    },
  })
}

function handleBackendVoiceError(message) {
  cleanupVoiceState()
  if (!voiceFallbackTried) {
    voiceFallbackTried = true
    try {
      startBrowserVoice(message)
      return
    } catch {
      // Fall through to show the backend error message.
    }
  }
  showToast(message || '这次没识别出来，请重试')
}

async function handleVoiceFinal(payload) {
  const text = String(payload?.text || payload || voicePreview.value || '').trim()
  cleanupVoiceState(text ? '转写完成。' : '录音结束。')
  if (!text) {
    showToast('这段录音没有整理出稳定文字，请再试一次')
    return
  }
  draft.value = mergeVoiceTranscriptIntoDraft(draft.value, text)
  showToast('语音已填入原句')
}

async function toggleVoiceInput() {
  if (voiceActive.value) {
    stopVoiceInput()
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
  try {
    voiceFallbackTried = false
    voiceStatus.value = '正在打开麦克风。'
    voicePreview.value = ''
    voiceController.value = createBackendRealtimeAsr({
      getSocketUrl: () => api.buildRealtimeAsrSocketUrl(),
      onActive: () => {
        voiceActive.value = true
        voiceFinalizing.value = false
      },
      onStatus: (text) => {
        voiceStatus.value = text
      },
      onPartial: (text) => {
        if (!voiceActive.value || voiceFinalizing.value) return
        voicePreview.value = text
        voiceStatus.value = '正在把语音转成文字。'
      },
      onFinal: handleVoiceFinal,
      onError: handleBackendVoiceError,
    })
    await voiceController.value.start()
  } catch (error) {
    try {
      startBrowserVoice(error.message)
    } catch (fallbackError) {
      cleanupVoiceState()
      showToast(describeVoiceStartError(fallbackError) || describeVoiceStartError(error))
    }
  }
}

function applyQuickDraft(text) {
  draft.value = text
  void loadPreview(true)
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
  if (refreshingRewrite.value || loading.value || !draft.value.trim()) return
  const scope = JSON.stringify([userStore.token, pairId.value, draft.value])
  const current = () => !pageDisposed && scope === JSON.stringify([userStore.token, pairId.value, draft.value])
  refreshingRewrite.value = true
  try {
    const reply = await requestSceneReply(api, pairId.value, {
      sourceLabel: '发前看看',
      summary: '原句：' + draft.value + '\n上一版：' + currentSaferRewrite.value,
    }, '运用高情商沟通套路换一种更加温柔委婉、有烟火气的说法。先体谅对方不易，再坦承自己的在乎与小失落，给出零压力的台阶和小请求，让人看一眼就心软想抱抱。绝不出现说教、算账或指责字眼，只返回改写文字。', current)
    if (current()) customRewrite.value = reply
  } catch (error) {
    if (current()) showToast(error.message || '这次没改出来，请重试。')
  } finally { refreshingRewrite.value = false }
}
async function handleSubmitAdjustment() {
  if (submittingFeedback.value) return
  if (!selectedFeedbackType.value && !feedbackNote.value.trim()) {
    showToast('请选择反馈类型或输入调整说明')
    return
  }
  submittingFeedback.value = true
  try {
    const feedbackType = selectedFeedbackType.value || 'somewhat_accurate'
    if (experienceMode.value.isDemoMode) {
      adjustmentSubmitted.value = true
      showToast('已记下本次样例反馈')
      return
    }
    const eventId = result.value?.event_id
    if (!eventId) throw new Error('这条结果暂时不能提交反馈。')
    await api.submitDecisionFeedback(eventId, feedbackType, feedbackNote.value.trim())
    adjustmentSubmitted.value = true
    showToast('已记录反馈')
  } catch (e) {
    showToast(e.message || '调整提交失败，请重试')
  } finally {
    submittingFeedback.value = false
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
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  color: rgba(92, 101, 109, 0.74);
  font-size: 12px;
  font-weight: 700;
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
}
</style>

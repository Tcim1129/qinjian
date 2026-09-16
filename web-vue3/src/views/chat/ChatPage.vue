<template>
  <div class="chat-page" :class="{ 'chat-page--embedded': embedded }">
    <section v-if="!embedded" class="page-head chat-head">
      <div class="chat-head__title-group">
        <p class="eyebrow">聊一聊</p>
        <h2>有什么想聊的？</h2>
      </div>
      <div class="chat-head__actions">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="startingNewTopic || voiceActive || voiceFinalizing" @click="startNewTopic">
          {{ startingNewTopic ? '切换中...' : '新话题' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="runningCheckup" @click="runCheckup">
          {{ runningCheckup ? '巡查中...' : '主动巡查' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="collaborating" @click="runCollaboration">
          {{ collaborating ? '协作中...' : '多智能体' }}
        </button>
        <button class="btn btn-secondary btn-sm" type="button" @click="moveToCheckin">
          整理成今日记录
          <ArrowUpRight :size="14" />
        </button>
      </div>
    </section>

    <section class="chat-shell">
      <header v-if="!embedded" class="chat-shell__toolbar">
        <div class="chat-shell__mode">
          <button
            class="voice-preference-trigger"
            type="button"
            :aria-expanded="voicePreferencePanelOpen"
            aria-controls="voice-preference-panel"
            @click="voicePreferencePanelOpen = !voicePreferencePanelOpen"
          >
            <Settings2 :size="14" />
            <span class="voice-preference-trigger__full">语音偏好：{{ voicePreferenceSummary }}</span>
            <span class="voice-preference-trigger__short">语音偏好</span>
            <strong>调整</strong>
          </button>
          <span class="chat-shell__privacy">最长 {{ recordingMaxSecondsLabel }} · {{ voiceSendPreferenceHint }}</span>
        </div>
      </header>

      <section
        v-if="voicePreferencePanelOpen"
        id="voice-preference-panel"
        class="voice-preference-panel"
        aria-label="语音偏好设置"
      >
        <div
          v-for="group in voicePreferenceGroups"
          :key="group.key"
          class="voice-preference-panel__group"
        >
          <span>{{ group.label }}</span>
          <div class="voice-preference-panel__options">
            <button
              v-for="option in group.options"
              :key="option.value"
              class="voice-preference-option"
              type="button"
              :class="{ active: voicePreferences[group.key] === option.value }"
              @click="setVoicePreference(group.key, option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </section>

      <article v-if="liveTranscript || voiceStatus" class="chat-live-card">
        <span>语音状态</span>
        <strong>{{ voiceStatus || (voiceActive ? '正在转写这段语音' : '语音已准备好') }}</strong>
        <span v-if="voiceActive" class="chat-live-card__timer">剩余 {{ recordingCountdownLabel }}</span>
        <p v-if="liveTranscript">{{ liveTranscript }}</p>
      </article>

      <article v-if="pendingVoiceEvidence" class="chat-pending-card">
        <div class="chat-pending-card__head">
          <div>
            <span>待发送录音</span>
            <strong>{{ pendingVoiceEvidence.source === 'upload' ? '上传录音' : '实时录音' }}</strong>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="clearPendingVoiceEvidence">
            <Trash2 :size="14" />
            清除
          </button>
        </div>
        <audio
          v-if="displayVoiceUrl(pendingVoiceEvidence)"
          class="chat-audio"
          :src="displayVoiceUrl(pendingVoiceEvidence)"
          controls
          preload="none"
        ></audio>
        <div v-if="hasVisibleVoiceInsight(pendingVoiceEvidence)" class="voice-insight-card">
          <div
            v-if="voiceInsightTags(pendingVoiceEvidence).length || emotionBlendSummary(pendingVoiceEvidence)"
            class="voice-insight-card__body"
          >
            <span>重点感受</span>
            <div v-if="voiceInsightTags(pendingVoiceEvidence).length" class="voice-insight-tags">
              <strong v-for="tag in voiceInsightTags(pendingVoiceEvidence)" :key="tag">{{ tag }}</strong>
            </div>
            <p v-if="emotionBlendSummary(pendingVoiceEvidence)">
              {{ emotionBlendSummary(pendingVoiceEvidence) }}
            </p>
          </div>
          <div v-if="voiceMetaItems(pendingVoiceEvidence).length" class="voice-insight-meta">
            <span v-for="item in voiceMetaItems(pendingVoiceEvidence)" :key="item">{{ item }}</span>
          </div>
        </div>
        <div v-else-if="hasHiddenEmotionNotice(pendingVoiceEvidence)" class="voice-insight-card voice-insight-card--muted">
          <span>情绪线索已保存</span>
        </div>
        <p class="chat-pending-card__transcript">
          {{ pendingVoiceEvidence.transcript_text || '录音已保存，但这次还没整理出稳定文字。' }}
        </p>
      </article>

      <div ref="messageListEl" class="chat-list">
        <div v-if="loadingHistory" class="empty-state">正在加载这段聊天...</div>
        <article v-if="checkupResult" class="chat-checkup-card">
          <header class="chat-checkup-card__head">
            <div>
              <span>主动巡查</span>
              <strong>{{ checkupRiskTitle }}</strong>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="checkupResult = null">
              <X :size="14" />
              关闭
            </button>
          </header>
          <p class="chat-checkup-card__report">{{ checkupResult.report }}</p>
          <div v-if="checkupActions.length" class="chat-checkup-card__actions">
            <span>建议推进</span>
            <strong v-for="(item, index) in checkupActions" :key="index">{{ item }}</strong>
          </div>
        </article>
        <article v-if="swarmResult" class="chat-swarm-card">
          <header class="chat-swarm-card__head">
            <div>
              <span>多智能体协作</span>
              <strong>感知 → 分析 → 行动 → 陪伴</strong>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="swarmResult = null">
              <X :size="14" />
              关闭
            </button>
          </header>
          <p class="chat-swarm-card__meta">共 {{ swarmResult.length }} 个角色接力 · 总耗时 {{ swarmTotalTime }}毫秒</p>
          <div class="chat-swarm-card__roles">
            <div v-for="(step, index) in swarmResult" :key="step.role" class="chat-swarm-card__role" :class="`is-${step.status}`">
              <div class="chat-swarm-card__role-title">
                <span class="chat-swarm-card__role-index">{{ index + 1 }}</span>
                <span class="chat-swarm-card__role-name">{{ step.role_name }}</span>
                <span class="chat-swarm-card__role-status">{{ swarmStatusLabel(step) }}</span>
                <span v-if="step.duration_ms" class="chat-swarm-card__role-time">{{ Math.round(step.duration_ms) }}ms</span>
              </div>
              <p class="chat-swarm-card__role-summary">{{ step.summary }}</p>
            </div>
          </div>
        </article>
        <div v-else-if="!messages.length" class="empty-state">
          先说一句，或者上传一段录音。
        </div>
        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-msg"
          :class="{ 'chat-msg--user': message.role === 'user', 'chat-msg--error': message.error }"
        >
          <div class="chat-msg__avatar">{{ message.role === 'user' ? '我' : '亲健' }}</div>
          <div class="chat-msg__bubble">
            <p class="chat-msg__text">{{ message.content }}</p>
            <div v-if="message.error" class="chat-msg__error-hint" role="alert">
              <p>{{ message.errorMessage || '这次没收到回复，原话还在。' }}</p>
              <button type="button" class="btn btn-ghost btn-sm" :disabled="sending || loadingHistory || startingNewTopic" @click="sendMessage({ retryMessage: message })">重试</button>
              <button type="button" class="btn btn-ghost btn-sm" :disabled="sending || Boolean(draft.trim())" @click="editFailedMessage(message)">重新编辑</button>
            </div>
            <details v-if="message.payload?.scene_context?.summary" class="chat-msg__reference">
              <summary>{{ message.payload.scene_context.source_label }} · 参考内容</summary>
              <p>{{ message.payload.scene_context.summary }}</p>
            </details>
            <AgentTaskProposals v-if="message.role === 'assistant'" :message="message" :session-id="sessionId" @confirmed="markTaskConfirmed(message, $event)" />
            <div v-if="message.role === 'assistant' && message.id === lastAssistantId" class="chat-msg__refinements">
              <button
                type="button"
                class="btn btn-ghost btn-sm btn-regenerate"
                :disabled="sending || loadingHistory || regeneratingId === message.id"
                @click="regenerateVariant(message)"
              >
                <RefreshCw :size="12" :class="{ 'is-spinning': regeneratingId === message.id }" />
                <span>{{ regeneratingId === message.id ? '换一种构思中...' : '换个说法' }}</span>
              </button>
              <button type="button" class="btn btn-ghost btn-sm" :disabled="sending || loadingHistory || regeneratingId === message.id" @click="refineReply('short')">短一点</button>
              <button type="button" class="btn btn-ghost btn-sm" :disabled="sending || loadingHistory || regeneratingId === message.id" @click="refineReply(sceneContext?.intent === 'plan' ? 'lighter' : 'direct')">{{ sceneContext?.intent === 'plan' ? '换个轻松的办法' : '直接一点' }}</button>
              <button type="button" class="btn btn-ghost btn-sm" @click="copyReply(message.content)">
                <Copy :size="12" />
                <span>复制</span>
              </button>
            </div>
            <div v-if="!message.role || message.role === 'assistant'">
              <button
                v-if="summarizeAgentTools(messageTrace(message)).length"
                class="chat-msg__trace-toggle"
                type="button"
                :aria-expanded="openTraceId === message.id"
                @click="toggleTrace(message.id)"
              >
                <span>查看实际调用</span>
              </button>
              <ul v-if="openTraceId === message.id" class="chat-msg__operations">
                <li v-for="operation in summarizeAgentTools(messageTrace(message))" :key="operation.key"><strong>{{ operation.label }}</strong><span>{{ operation.summary }}</span></li>
              </ul>
            </div>
            <div v-if="messageVoiceEvidence(message)" class="chat-msg__evidence">
              <audio
                v-if="displayVoiceUrl(messageVoiceEvidence(message))"
                class="chat-audio"
                :src="displayVoiceUrl(messageVoiceEvidence(message))"
                controls
                preload="none"
              ></audio>
              <div v-if="hasVisibleVoiceInsight(messageVoiceEvidence(message))" class="voice-insight-card">
                <div
                  v-if="voiceInsightTags(messageVoiceEvidence(message)).length || emotionBlendSummary(messageVoiceEvidence(message))"
                  class="voice-insight-card__body"
                >
                  <span>重点感受</span>
                  <div v-if="voiceInsightTags(messageVoiceEvidence(message)).length" class="voice-insight-tags">
                    <strong v-for="tag in voiceInsightTags(messageVoiceEvidence(message))" :key="tag">{{ tag }}</strong>
                  </div>
                  <p v-if="emotionBlendSummary(messageVoiceEvidence(message))">
                    {{ emotionBlendSummary(messageVoiceEvidence(message)) }}
                  </p>
                </div>
                <div v-if="voiceMetaItems(messageVoiceEvidence(message)).length" class="voice-insight-meta">
                  <span v-for="item in voiceMetaItems(messageVoiceEvidence(message))" :key="item">{{ item }}</span>
                </div>
              </div>
              <div v-else-if="hasHiddenEmotionNotice(messageVoiceEvidence(message))" class="voice-insight-card voice-insight-card--muted">
                <span>情绪线索已保存</span>
              </div>
              <p
                v-if="messageVoiceEvidence(message)?.transcript_text && messageVoiceEvidence(message)?.transcript_text !== message.content"
                class="chat-msg__transcript"
              >
                {{ messageVoiceEvidence(message).transcript_text }}
              </p>
            </div>
          </div>
        </article>
        <div v-if="sending" class="chat-waiting" role="status" aria-live="polite"><span class="chat-spinner" aria-hidden="true"></span>正在回复…</div>
      </div>
      <p v-if="sendError" class="chat-send-error" role="alert">{{ sendError }}</p>

      <div v-if="!embedded && demoSuggestedQuestions.length" class="chat-suggestions-bar">
        <div class="chat-suggestions-bar__header">
          <div class="chat-suggestions-bar__title-wrap">
            <span class="chat-suggestions-bar__dot"></span>
            <span class="chat-suggestions-bar__title">{{ currentDemoQA?.name ? `${currentDemoQA.name} 专属推荐` : '快捷提问' }}</span>
            <span v-if="currentDemoQA?.scenarioDescription" class="chat-suggestions-bar__scenario">· {{ currentDemoQA.scenarioDescription }}</span>
          </div>
          <span class="chat-suggestions-bar__hint">点击即发</span>
        </div>
        <div class="chat-suggestions-bar__list">
          <button
            v-for="(q, idx) in demoSuggestedQuestions"
            :key="idx"
            type="button"
            class="chat-suggestion-chip"
            :disabled="sending"
            @click="askSuggestedQuestion(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <footer class="chat-composer">
        <label class="field chat-composer__field">
          <textarea
            ref="composerInput"
            v-model="draft"
            class="input input-textarea chat-composer__input"
            :placeholder="composerPlaceholder"
            rows="2"
            aria-label="想说的话"
            @keydown.enter="handleEnterKey"
          ></textarea>
        </label>
        <div class="chat-composer__actions">
          <button class="btn btn-ghost btn-sm" type="button" :disabled="uploadingVoice || sending || experienceMode.isDemoMode" @click="openVoiceUpload">
            <Upload :size="15" />
            上传录音
          </button>
          <button
            class="btn btn-sm"
            :class="voiceActive ? 'btn-secondary' : 'btn-ghost'"
            type="button"
            :disabled="sending || voiceFinalizing"
            @click="toggleVoiceInput"
          >
            <component :is="voiceActive ? StopCircle : Mic" :size="15" />
            {{ voiceButtonLabel }}
          </button>
          <button class="btn btn-primary btn-sm btn-send" type="button" :disabled="!canSend" @click="sendMessage()">
            <span v-if="sending" class="chat-spinner" aria-hidden="true"></span>
            <SendHorizontal v-else :size="15" />
            {{ sending ? '回复中...' : '发送' }}
          </button>
        </div>
      </footer>

      <input ref="voiceInput" type="file" accept="audio/*" class="hidden" @change="handleVoiceUpload" />
    </section>
  </div>
</template>

<script setup>
import { ArrowUpRight, Copy, Mic, RefreshCw, SendHorizontal, Settings2, StopCircle, Trash2, Upload, X } from 'lucide-vue-next'
import { computed, inject, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api, isRealAgentEnabled } from '@/api'
import { inspectVoiceFile } from '@/utils/clientAi'
import { saveChatDraftToCheckin } from '@/utils/checkinDraftBridge'
import AgentTaskProposals from '@/components/AgentTaskProposals.vue'
import { buildSceneContext, isChatScopeCurrent, summarizeAgentTools } from '@/utils/contextAgent'
import { AI_WAITING_NOTICE, VOICE_TRANSCRIPTION_WAITING_NOTICE } from '@/utils/aiWaitFeedback'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { getDemoPersonaQA } from '@/demo/fixtures'
import { mergeChatHistory } from '@/utils/chatHistory'
import {
  DEFAULT_REALTIME_MAX_SECONDS,
  describeVoiceStartError,
  formatRecordingCountdown,
  createBackendRealtimeAsr,
} from '@/utils/realtimeVoice'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  isolated: { type: Boolean, default: false },
  contextPairId: { type: String, default: undefined },
  sceneContext: { type: Object, default: null },
})

const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast')

const VOICE_PREFERENCE_STORAGE_KEY = 'qinjian-chat-voice-preferences'
const defaultVoicePreferences = {
  rhythm: 'light',
  emotion: 'gentle',
  sending: 'auto',
}
const voicePreferenceGroups = [
  {
    key: 'rhythm',
    label: '互动节奏',
    options: [
      { value: 'light', label: '轻陪伴' },
      { value: 'organize', label: '边聊边整理' },
      { value: 'lead', label: '主动带节奏' },
    ],
  },
  {
    key: 'emotion',
    label: '情绪呈现',
    options: [
      { value: 'gentle', label: '温柔观察' },
      { value: 'evidence', label: '标签线索' },
      { value: 'hidden', label: '默认隐藏' },
    ],
  },
  {
    key: 'sending',
    label: '录音发送',
    options: [
      { value: 'auto', label: '自动发送' },
      { value: 'manual', label: '手动确认' },
    ],
  },
]

function readStoredVoicePreferences() {
  if (typeof window === 'undefined') return { ...defaultVoicePreferences }
  try {
    const raw = window.localStorage.getItem(VOICE_PREFERENCE_STORAGE_KEY)
    const saved = raw ? JSON.parse(raw) : {}
    return {
      rhythm: voicePreferenceGroups[0].options.some((option) => option.value === saved?.rhythm) ? saved.rhythm : defaultVoicePreferences.rhythm,
      emotion: voicePreferenceGroups[1].options.some((option) => option.value === saved?.emotion) ? saved.emotion : defaultVoicePreferences.emotion,
      sending: voicePreferenceGroups[2].options.some((option) => option.value === saved?.sending) ? saved.sending : defaultVoicePreferences.sending,
    }
  } catch {
    return { ...defaultVoicePreferences }
  }
}

const loadingHistory = ref(false)
const sending = ref(false)
const uploadingVoice = ref(false)
const startingNewTopic = ref(false)
const messages = ref([])
const lastAssistantId = computed(() => messages.value.findLast(item => item.role === 'assistant')?.id)
const draft = ref('')
const sessionId = ref('')
const sessionExpiresAt = ref('')
const voicePreferencePanelOpen = ref(false)
const voicePreferences = reactive(readStoredVoicePreferences())
const autoSendVoice = ref(voicePreferences.sending === 'auto')
const voiceInput = ref(null)
const composerInput = ref(null)
const messageListEl = ref(null)
const voiceController = ref(null)
const voiceActive = ref(false)
const voiceFinalizing = ref(false)
const voiceStatus = ref('')
const liveTranscript = ref('')
const pendingVoiceEvidence = ref(null)
const recordingMaxSeconds = DEFAULT_REALTIME_MAX_SECONDS
const recordingRemainingSeconds = ref(DEFAULT_REALTIME_MAX_SECONDS)
const openTraceId = ref('')
const runningCheckup = ref(false)
const sendError = ref('')
const checkupResult = ref(null)
const collaborating = ref(false)
const swarmResult = ref(null)
let chatDisposed = false
let pendingSessionRequest = null
let chatRevision = 0

function captureChatScope() { return { token: userStore.token, userId: userStore.me?.id, pairId: activePairId.value, revision: chatRevision, disposed: chatDisposed } }
function assertChatScope(scope) {
  if (!isChatScopeCurrent(scope, captureChatScope())) throw new Error('聊天已关闭或关系已切换，请重新进入。')
}

const activePairId = computed(() => props.contextPairId !== undefined ? props.contextPairId : userStore.activePairId || null)
const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: activePairId.value,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const currentDemoQA = computed(() => getDemoPersonaQA(activePairId.value))
const demoSuggestedQuestions = computed(() => currentDemoQA.value?.suggestedQuestions || [])

function loadPersonaQA(personaId) {
  const qa = getDemoPersonaQA(personaId)
  messages.value = (qa?.initialMessages || []).map(normalizeMessage)
  scrollMessagesToBottom()
}

function handleEnterKey(event) {
  if (event.isComposing) return
  if (!event.shiftKey) {
    event.preventDefault()
    if (canSend.value) {
      sendMessage()
    }
  }
}

async function askSuggestedQuestion(q) {
  if (sending.value) return
  draft.value = q
  await sendMessage()
}

const realAgentDemo = computed(() => isRealAgentEnabled())
const canSend = computed(() => {
  const hasText = Boolean(String(draft.value || '').trim())
  const hasTranscript = Boolean(String(pendingVoiceEvidence.value?.transcript_text || '').trim())
  return !loadingHistory.value && !sending.value && !voiceActive.value && !voiceFinalizing.value && (hasText || hasTranscript)
})
const voiceButtonLabel = computed(() => {
  if (voiceFinalizing.value) return '收尾中...'
  if (voiceActive.value) return autoSendVoice.value ? '停止并发送' : '停止录音'
  return '开始录音'
})
const recordingCountdownLabel = computed(() => formatRecordingCountdown(recordingRemainingSeconds.value))
const recordingMaxSecondsLabel = computed(() => {
  if (recordingMaxSeconds >= 60) return `${Math.round(recordingMaxSeconds / 60)} 分钟`
  return `${recordingMaxSeconds} 秒`
})
const voicePreferenceSummary = computed(() => {
  const rhythm = preferenceLabel('rhythm', voicePreferences.rhythm)
  const emotion = preferenceLabel('emotion', voicePreferences.emotion)
  return `${rhythm} · ${emotion}`
})
const voiceSendPreferenceHint = computed(() => (
  voicePreferences.sending === 'auto' ? '停止后自动发送' : '停止后先确认'
))
const emotionDisplayMode = computed(() => voicePreferences.emotion)
const shouldShowEmotionInsight = computed(() => emotionDisplayMode.value !== 'hidden')
const shouldShowDetailedEvidence = computed(() => emotionDisplayMode.value === 'evidence')
const composerHint = computed(() => {
  if (experienceMode.value.isDemoMode && !realAgentDemo.value) return featureUnavailableReason('demo-online', experienceMode.value)
  if (sending.value) return '亲健正在回复。'
  if (voiceFinalizing.value) return '正在保存录音。'
  if (voiceActive.value) {
    return autoSendVoice.value
      ? `剩余 ${recordingCountdownLabel.value}，停下后发送。`
      : `剩余 ${recordingCountdownLabel.value}，停下后进草稿。`
  }
  if (pendingVoiceEvidence.value && !draft.value.trim()) {
    return '录音已就位，可直接发。'
  }
  return '支持打字、录音、上传。'
})

const composerPlaceholder = computed(() => {
  if (experienceMode.value.isDemoMode) {
    const activeId = String(userStore.activePairId || '')
    if (activeId.includes('22222222')) {
      return '想和林夏说点什么？输入你想说的话，或者点击上方推荐问题试试~'
    } else if (activeId.includes('77777777')) {
      return '想找周宁聊点什么？可以吐槽、调侃，或者问问怎么破冰~'
    } else if (activeId.includes('99999999')) {
      return '想和顾遥对齐什么？关于分工、催进度或者约球都可以问~'
    }
    return '把你想说的话写在这儿，或者输入你最近纠结的沟通小困扰~'
  }
  return '输入你想说的话，或者倾诉最近在关系里遇到的小纠结~'
})

function notify(message) {
  if (message) showToast?.(message)
}

function preferenceLabel(groupKey, value) {
  const group = voicePreferenceGroups.find((item) => item.key === groupKey)
  return group?.options.find((option) => option.value === value)?.label || ''
}

function persistVoicePreferences() {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(VOICE_PREFERENCE_STORAGE_KEY, JSON.stringify({ ...voicePreferences }))
  } catch {
    // 偏好保存失败不影响当前会话使用。
  }
}

function setVoicePreference(groupKey, value) {
  if (!Object.prototype.hasOwnProperty.call(voicePreferences, groupKey)) return
  voicePreferences[groupKey] = value
  if (groupKey === 'sending') {
    autoSendVoice.value = value === 'auto'
  }
  persistVoicePreferences()
}

function isAgentSessionExpired() {
  if (!sessionExpiresAt.value) return false
  const expiresAt = Date.parse(sessionExpiresAt.value)
  return Number.isFinite(expiresAt) && expiresAt <= Date.now()
}

function normalizeMessage(message) {
  const delivery = message?.payload?._delivery
  return {
    id: message?.id || `message-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role: message?.role || 'assistant',
    content: String(message?.content || '').trim(),
    payload: message?.payload || null,
    trace: Array.isArray(message?.trace) ? message.trace : [],
    clientMessageId: message?.role === 'user' && delivery ? message.id : null,
    error: message?.role === 'user' && delivery && delivery.state !== 'completed',
    errorMessage: delivery?.state === 'processing' ? '回复还未确认，请稍后重试。' : '',
  }
}

function normalizeVoiceEvidence(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    voice_url: String(raw.voice_url || '').trim(),
    playback_url: String(raw.playback_url || '').trim(),
    transcript_text: String(raw.transcript_text || '').trim(),
    duration_seconds: raw.duration_seconds ?? null,
    source: String(raw.source || '').trim() || 'upload',
    voice_emotion: raw.voice_emotion || null,
    content_emotion: raw.content_emotion || null,
    transcript_language: raw.transcript_language || null,
  }
}

function displayVoiceUrl(evidence) {
  return String(evidence?.playback_url || evidence?.voice_url || '').trim()
}

function voiceEmotionLabel(evidence) {
  return String(evidence?.voice_emotion?.label || evidence?.voice_emotion?.code || '').trim()
}

function uniqueStrings(items, limit = 3) {
  const result = []
  for (const item of Array.isArray(items) ? items : []) {
    const value = String(item || '').trim()
    if (value && !result.includes(value)) result.push(value)
    if (result.length >= limit) break
  }
  return result
}

function firstNonEmptyArray(...candidates) {
  return candidates.find((items) => Array.isArray(items) && items.length) || []
}

function contentEmotionTags(evidence) {
  const emotion = evidence?.content_emotion || {}
  const profile = emotion.emotion_profile || {}
  const userFacing = emotion.user_facing || {}
  return uniqueStrings(
    firstNonEmptyArray(
      userFacing.display_mood_tags,
      emotion.display_mood_tags,
      profile.display_mood_tags,
      emotion.mood_tags,
      [
        emotion.primary_mood,
        ...(Array.isArray(emotion.secondary_moods) ? emotion.secondary_moods : []),
      ],
    ),
    3,
  )
}

function contentEmotionLabel(evidence) {
  const tags = contentEmotionTags(evidence)
  if (tags.length) return tags.join(' · ')
  return String(
    evidence?.content_emotion?.mood_label
    || evidence?.content_emotion?.primary_mood
    || evidence?.content_emotion?.sentiment_label
    || evidence?.content_emotion?.sentiment
    || ''
  ).trim()
}

function voiceInsightTags(evidence) {
  const tags = contentEmotionTags(evidence)
  if (tags.length) return tags
  const fallback = contentEmotionLabel(evidence)
  return fallback ? [fallback] : []
}

function emotionBlendSummary(evidence) {
  const emotion = evidence?.content_emotion || {}
  return String(
    emotion.user_facing?.blend_summary
      || emotion.emotion_blend_summary
      || emotion.emotion_profile?.blend_summary
      || emotion.reason
      || '',
  ).trim()
}

function languageLabel(evidence) {
  return String(evidence?.transcript_language?.label || evidence?.transcript_language?.code || '').trim()
}

function hasHiddenEmotionNotice(evidence) {
  return !shouldShowEmotionInsight.value
    && Boolean(voiceInsightTags(evidence).length || emotionBlendSummary(evidence) || voiceEmotionLabel(evidence))
}

function hasVisibleVoiceInsight(evidence) {
  return shouldShowEmotionInsight.value
    && Boolean(voiceInsightTags(evidence).length || emotionBlendSummary(evidence) || voiceMetaItems(evidence).length)
}

function formatSeconds(value) {
  const seconds = Number(value || 0)
  if (!Number.isFinite(seconds) || seconds <= 0) return '--'
  if (seconds < 60) return `${seconds.toFixed(seconds >= 10 ? 0 : 1)} 秒`
  const minutes = Math.floor(seconds / 60)
  const remain = Math.round(seconds % 60)
  return `${minutes} 分 ${remain} 秒`
}

function voiceMetaItems(evidence) {
  const items = []
  if (evidence?.duration_seconds) items.push(`时长 ${formatSeconds(evidence.duration_seconds)}`)
  if (shouldShowDetailedEvidence.value && voiceEmotionLabel(evidence)) items.push(`语气 ${voiceEmotionLabel(evidence)}`)
  if (languageLabel(evidence)) items.push(languageLabel(evidence))
  return items
}

function messageVoiceEvidence(message) {
  return normalizeVoiceEvidence(message?.payload?.voice_evidence)
}

function mergeTranscriptText(base, transcript) {
  const current = String(base || '').trim()
  const incoming = String(transcript || '').trim()
  if (!incoming) return current
  if (!current) return incoming
  if (current.includes(incoming)) return current
  return `${current}\n${incoming}`
}

function extensionFromMimeType(mimeType) {
  const normalized = String(mimeType || '').toLowerCase()
  if (normalized.includes('ogg')) return 'ogg'
  if (normalized.includes('mp4') || normalized.includes('aac')) return 'm4a'
  if (normalized.includes('mpeg') || normalized.includes('mp3')) return 'mp3'
  if (normalized.includes('wav')) return 'wav'
  return 'webm'
}

function createAudioFileFromBlob(blob) {
  const type = String(blob?.type || 'audio/webm').trim() || 'audio/webm'
  return new File([blob], `chat-voice-${Date.now()}.${extensionFromMimeType(type)}`, { type })
}

function buildEvidenceForRequest(evidence) {
  if (!evidence) return undefined
  return {
    voice_url: evidence.voice_url || null,
    transcript_text: evidence.transcript_text || '',
    duration_seconds: evidence.duration_seconds ?? null,
    source: evidence.source || 'upload',
    voice_emotion: evidence.voice_emotion || null,
    content_emotion: evidence.content_emotion || null,
    transcript_language: evidence.transcript_language || null,
  }
}

function buildEvidenceForDisplay(evidence) {
  if (!evidence) return null
  return {
    ...buildEvidenceForRequest(evidence),
    voice_url: displayVoiceUrl(evidence),
  }
}

function scrollMessagesToBottom() {
  nextTick(() => {
    const container = messageListEl.value
    if (container) {
      container.scrollTop = container.scrollHeight
      setTimeout(() => {
        if (container) container.scrollTop = container.scrollHeight
      }, 60)
    }
  })
}

function cleanupVoiceState(status = '') {
  voiceActive.value = false
  voiceFinalizing.value = false
  voiceStatus.value = status
  liveTranscript.value = ''
  recordingRemainingSeconds.value = recordingMaxSeconds
  voiceController.value = null
}

function stopVoiceInput({ discard = false } = {}) {
  if (!voiceController.value) {
    cleanupVoiceState()
    return
  }
  voiceActive.value = false
  voiceFinalizing.value = !discard
  voiceStatus.value = discard ? '' : '正在保存最后一段录音。'
  voiceController.value.stop?.({ discard })
  if (discard) cleanupVoiceState()
}

async function ensureAgentSession({ forceNew = false } = {}) {
  if (experienceMode.value.isDemoMode && !realAgentDemo.value) {
    throw new Error(featureUnavailableReason('demo-online', experienceMode.value))
  }
  const expired = !forceNew && sessionId.value && isAgentSessionExpired()
  if (expired) {
    sessionId.value = ''
    sessionExpiresAt.value = ''
    messages.value = messages.value.filter(message => message.error || message.deliveryPending)
  }
  if (sessionId.value && !forceNew) return sessionId.value
  if (pendingSessionRequest && !forceNew) return pendingSessionRequest
  const scope = captureChatScope()
  assertChatScope(scope)
  const request = (async () => {
    const session = await api.createAgentSession(scope.pairId, {
      forceNew: forceNew || (props.isolated && !sessionId.value),
      surface: 'chat',
    })
    assertChatScope(scope)
    const resolvedId = session.session_id || session.id
    const history = await api.getAgentMessages(resolvedId).catch(() => [])
    assertChatScope(scope)
    sessionId.value = resolvedId
    sessionExpiresAt.value = session.expires_at || ''
    if (forceNew) messages.value = []
    else if (Array.isArray(history) && history.length) {
      const normalizedHistory = history.filter((item) => item.role === 'user' || item.role === 'assistant').map(normalizeMessage)
      messages.value = mergeChatHistory(normalizedHistory, messages.value)
    }
    scrollMessagesToBottom()
    return resolvedId
  })()
  pendingSessionRequest = request
  try { return await request }
  finally { if (pendingSessionRequest === request) pendingSessionRequest = null }
}

async function loadInitialSession() {
  const scope = captureChatScope()
  if (experienceMode.value.isDemoMode) {
    if (props.isolated) messages.value = []
    else loadPersonaQA(activePairId.value)
    if (realAgentDemo.value) {
      ensureAgentSession().catch((err) => {
        console.warn('Demo session prewarm skipped:', err)
      })
    }
    return true
  }
  loadingHistory.value = true
  try {
    await ensureAgentSession()
    return true
  } catch (error) {
    if (isChatScopeCurrent(scope, captureChatScope())) notify(error.message || '暂时无法打开聊天页')
    return false
  } finally {
    if (isChatScopeCurrent(scope, captureChatScope())) loadingHistory.value = false
  }
}

function clearPendingVoiceEvidence() {
  pendingVoiceEvidence.value = null
}

function newClientMessageId() {
  // getRandomValues also works on non-HTTPS local/LAN origins.
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function editFailedMessage(message) {
  if (sending.value || draft.value.trim()) return
  draft.value = message.content
  focusComposer()
}

async function sendMessage({ overrideContent = null, overrideEvidence = null, retryMessage = null } = {}) {
  if (chatDisposed || loadingHistory.value || sending.value || startingNewTopic.value) return false
  if (retryMessage && (!messages.value.includes(retryMessage) || !retryMessage.error)) return false
  sendError.value = ''
  const sendScope = captureChatScope()
  const currentDraft = String(retryMessage?.content ?? overrideContent ?? draft.value ?? '').trim()
  const currentEvidence = retryMessage
    ? normalizeVoiceEvidence(retryMessage.payload?.voice_evidence)
    : normalizeVoiceEvidence(overrideEvidence ?? pendingVoiceEvidence.value)
  const finalContent = currentDraft || String(currentEvidence?.transcript_text || '').trim()
  if (!finalContent) {
    notify('先写一句，或者先准备一段录音')
    return false
  }

  const clientMessageId = retryMessage?.clientMessageId || newClientMessageId()
  const optimisticId = `local-user-${clientMessageId}`
  const scene = retryMessage?.payload?.scene_context || (props.sceneContext ? buildSceneContext(props.sceneContext) : null)
  const optimisticMessage = retryMessage || reactive(normalizeMessage({
    id: optimisticId,
    role: 'user',
    content: finalContent,
    payload: {
      surface: 'chat',
      ...(scene ? { scene_context: scene } : {}),
      ...(currentEvidence ? { voice_evidence: buildEvidenceForDisplay(currentEvidence) } : {}),
    },
  }))
  optimisticMessage.clientMessageId = clientMessageId
  optimisticMessage.error = false
  optimisticMessage.errorMessage = ''
  optimisticMessage.deliveryPending = true
  // 用户消息立即推入聊天列表，始终予以保留
  if (!retryMessage) {
    draft.value = ''
    if (!overrideEvidence || overrideEvidence === pendingVoiceEvidence.value) pendingVoiceEvidence.value = null
    messages.value.push(optimisticMessage)
  }
  scrollMessagesToBottom()

  // 样例只提供可浏览的历史；新消息始终使用真实接口。
  sending.value = true
  try {
    const resolvedSessionId = await ensureAgentSession()
    assertChatScope(sendScope)

    // 标注为虚构的关系背景，不能要求助手扮演另一方。
    const demoScene = (experienceMode.value.isDemoMode && currentDemoQA.value) ? {
      intent: 'auto',
      source_label: `${currentDemoQA.value.name}（${currentDemoQA.value.roleLabel}）`,
      summary: `【虚构关系样例】用户正在讨论与${currentDemoQA.value.name}（${currentDemoQA.value.roleLabel}）的相处。背景：${currentDemoQA.value.scenarioDescription || ''}。你仍是亲健助手，不扮演对方，不把样例当作用户真实经历。`,
    } : null
    const effectiveScene = scene || demoScene

    const request = optimisticMessage.request || {
      client_message_id: clientMessageId,
      content: currentDraft || finalContent,
      surface: 'chat',
      voice_evidence: buildEvidenceForRequest(currentEvidence),
      ...(effectiveScene ? { scene_context: effectiveScene } : {}),
    }
    optimisticMessage.request = request
    const response = await api.chatWithAgent(resolvedSessionId, request)
    assertChatScope(sendScope)
    if (!String(response?.reply || response?.content || '').trim()) throw new Error('这次没有收到回复，请重试。')
    optimisticMessage.deliveryPending = false
    optimisticMessage.id = clientMessageId
    const assistantMessage = normalizeMessage({
      id: response?.message_id || `local-assistant-${Date.now()}`,
      role: 'assistant',
      content: response?.reply || response?.content,
      payload: {
        task_proposals: response?.task_proposals || [],
        ...(effectiveScene ? { scene_context: effectiveScene } : {}),
      },
      trace: Array.isArray(response?.trace) ? response.trace : [],
    })
    if (!messages.value.some(message => message.id === assistantMessage.id)) messages.value.push(assistantMessage)
    scrollMessagesToBottom()
    return true
  } catch (error) {
    if (!isChatScopeCurrent(sendScope, captureChatScope())) return false

    // 标记乐观消息失败状态，但不从消息流中移除，保留用户输入事实
    optimisticMessage.error = true
    optimisticMessage.deliveryPending = false
    optimisticMessage.errorMessage = error.message || '这次没能收到回复，请重试。'
    sendError.value = error.message || '这次没能收到回复，请重试。'
    notify(sendError.value)
    return false
  } finally {
    if (isChatScopeCurrent(sendScope, captureChatScope())) sending.value = false
  }
}

function applySuggestedPrompt(text) {
  draft.value = String(text || '').trim()
  nextTick(() => focusComposer())
}

function focusComposer() {
  composerInput.value?.focus?.()
}

async function beginScene(text) {
  applySuggestedPrompt(text)
  const ready = await loadInitialSession()
  if (!ready || chatDisposed) return false
  return sendMessage()
}

const regeneratingId = ref('')

async function regenerateVariant(targetMessage) {
  if (sending.value || loadingHistory.value || regeneratingId.value) return
  if (!targetMessage) return
  const scope = captureChatScope()

  const msgIdx = messages.value.findIndex((m) => m.id === targetMessage.id)
  let previousUserMessage = null
  if (msgIdx > 0) {
    for (let i = msgIdx - 1; i >= 0; i--) {
      if (messages.value[i].role === 'user') {
        previousUserMessage = messages.value[i]
        break
      }
    }
  }
  const originalQuestion = previousUserMessage?.content || targetMessage.content || '请根据当前设定换一种说法'

  regeneratingId.value = targetMessage.id
  notify('正在按当前人物背景，换一种角度重新构思...')

  try {
    const resolvedSessionId = await ensureAgentSession()
    assertChatScope(scope)
    const demoSceneContext = experienceMode.value.isDemoMode && currentDemoQA.value ? {
      intent: 'auto',
      source_label: `${currentDemoQA.value.name}（${currentDemoQA.value.roleLabel}）`,
      summary: `【${currentDemoQA.value.name}专属场景】${currentDemoQA.value.scenarioDescription}`,
    } : null

    const prompt = `针对之前的提问「${originalQuestion}」，请换一种更加自然贴切、有生活感或者更轻松幽默的切入角度和口吻重新回复。严格遵循人设背景与避雷偏好，提供高情绪价值，给出可直接做的小事或可直接说的原话。`

    const response = await api.chatWithAgent(resolvedSessionId, {
      content: prompt,
      surface: 'chat',
      ...(props.sceneContext ? { scene_context: buildSceneContext(props.sceneContext) } : (demoSceneContext ? { scene_context: demoSceneContext } : {})),
    })

    assertChatScope(scope)
    const newReply = response?.reply || response?.content
    if (!String(newReply || '').trim()) throw new Error('这次没有收到回复，请重试。')
    if (newReply) {
      targetMessage.content = newReply
      if (Array.isArray(response?.trace) && response.trace.length) {
        targetMessage.trace = response.trace
      }
      scrollMessagesToBottom()
      notify('已换一种说法重新构思~')
      return
    }
  } catch (err) {
    if (isChatScopeCurrent(scope, captureChatScope())) {
      notify(err.message || '换个说法暂时受阻，请稍后重试')
    }
  } finally {
    regeneratingId.value = ''
  }
}

function refineReply(kind) {
  const prompts = {
    short: '再短一点，保留我原本的意思。',
    direct: '说得直接一点，但不要替我下结论，也不要变成指责。',
    lighter: '这个办法对我来说有点费劲，换一个更轻松的。',
  }
  if (draft.value.trim()) { notify('先发出或清空正在写的话，再调整回复'); return }
  return sendMessage({ overrideContent: prompts[kind] })
}

async function copyReply(text) {
  try { await navigator.clipboard.writeText(text); notify('已复制') }
  catch { notify('暂时无法复制，可以长按选中文字') }
}

defineExpose({ applySuggestedPrompt, focusComposer, beginScene })

async function handleUploadedVoiceFile(file) {
  const inspected = await inspectVoiceFile(file).catch(() => null)
  const upload = await api.uploadFile('voice', file)
  let transcription = null
  try {
    notify(VOICE_TRANSCRIPTION_WAITING_NOTICE)
    transcription = await api.transcribeVoice(file)
  } catch (error) {
    notify(error.message || '录音已保存，但这次没能顺利转写')
  }
  pendingVoiceEvidence.value = normalizeVoiceEvidence({
    voice_url: upload?.url || '',
    playback_url: upload?.access_url || upload?.url || '',
    transcript_text: String(transcription?.text || '').trim(),
    duration_seconds: inspected?.deviceMeta?.duration_seconds ?? null,
    source: 'upload',
    voice_emotion: transcription?.voice_emotion || null,
    content_emotion: transcription?.content_emotion || null,
    transcript_language: transcription?.transcript_language || null,
  })
}

async function handleVoiceUpload(event) {
  const file = event.target.files?.[0]
  if (voiceInput.value) voiceInput.value.value = ''
  if (!file) return
  if (experienceMode.value.isDemoMode) {
    notify(featureUnavailableReason('voice', experienceMode.value))
    return
  }
  uploadingVoice.value = true
  try {
    await handleUploadedVoiceFile(file)
    notify('录音已放进待发送材料里')
  } catch (error) {
    notify(error.message || '录音没传上，请稍后再试')
  } finally {
    uploadingVoice.value = false
  }
}

function openVoiceUpload() {
  if (experienceMode.value.isDemoMode) {
    notify(featureUnavailableReason('voice', experienceMode.value))
    return
  }
  voiceInput.value?.click()
}

async function handleRealtimeFinal(result) {
  const transcript = String(result?.text || liveTranscript.value || '').trim()
  let upload = null
  if (result?.rawAudioBlob) {
    try {
      const audioFile = createAudioFileFromBlob(result.rawAudioBlob)
      upload = await api.uploadFile('voice', audioFile)
    } catch (error) {
      notify(error.message || '原始录音没保存上，这轮先保留转写文字')
    }
  }

  const evidence = normalizeVoiceEvidence({
    voice_url: upload?.url || '',
    playback_url: upload?.access_url || upload?.url || '',
    transcript_text: transcript,
    duration_seconds: result?.durationSeconds ?? null,
    source: 'realtime',
    voice_emotion: result?.voiceEmotion || null,
    content_emotion: result?.contentEmotion || null,
    transcript_language: result?.transcriptLanguage || null,
  })

  cleanupVoiceState(transcript ? '这一段已经整理好了。' : '录音结束。')
  pendingVoiceEvidence.value = evidence
  if (!transcript) {
    notify('这段录音没有整理出稳定文字，请再试一次')
    return
  }

  if (autoSendVoice.value) {
    await sendMessage({
      overrideContent: transcript,
      overrideEvidence: evidence,
    })
    return
  }

  draft.value = mergeTranscriptText(draft.value, transcript)
    notify('录音已放进草稿，可改字再发')
}

function handleVoiceError(message) {
  const text = String(message || '').trim() || '这次没识别出来，请重试'
  const partialTranscript = String(liveTranscript.value || '').trim()
  cleanupVoiceState(text)
  if (partialTranscript) {
    draft.value = mergeTranscriptText(draft.value, partialTranscript)
    notify(`${text} 已把听到的文字放进草稿，也可以上传录音或改用文字。`)
    return
  }
  notify(`${text} 可以上传录音或改用文字。`)
}

async function toggleVoiceInput() {
  if (voiceActive.value) {
    stopVoiceInput()
    return
  }
  if (voiceFinalizing.value) {
    notify('正在保存最后一段录音')
    return
  }
  if (!experienceMode.value.canUseVoice) {
    notify(featureUnavailableReason('voice', experienceMode.value))
    return
  }
  try {
    voiceStatus.value = '正在打开麦克风。'
    recordingRemainingSeconds.value = recordingMaxSeconds
    voiceController.value = createBackendRealtimeAsr({
      captureRawAudio: true,
      maxDurationSeconds: recordingMaxSeconds,
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
        liveTranscript.value = text
        voiceStatus.value = '正在转写，可能会有少量错字。'
      },
      onTick: ({ remainingSeconds }) => {
        if (!voiceActive.value || voiceFinalizing.value) return
        recordingRemainingSeconds.value = remainingSeconds
      },
      onTimeLimit: () => {
        voiceStatus.value = `已到 ${recordingMaxSecondsLabel.value} 上限，正在保存这段语音。`
      },
      onFinal: handleRealtimeFinal,
      onError: handleVoiceError,
    })
    await voiceController.value.start()
  } catch (error) {
    cleanupVoiceState()
    notify(describeVoiceStartError(error))
  }
}

async function startNewTopic() {
  if (startingNewTopic.value || sending.value || voiceActive.value || voiceFinalizing.value) return
  if (experienceMode.value.isDemoMode && !realAgentDemo.value) {
    notify(featureUnavailableReason('demo-online', experienceMode.value))
    return
  }
  startingNewTopic.value = true
  chatRevision++
  pendingSessionRequest = null
  try {
    await ensureAgentSession({ forceNew: true })
    notify('已经切到新的聊天话题')
  } catch (error) {
    notify(error.message || '暂时不能开启新话题')
  } finally {
    startingNewTopic.value = false
  }
}

function moveToCheckin() {
  const latestUserMessage = [...messages.value].reverse().find((item) => item.role === 'user')
  const draftContent = String(draft.value || '').trim()
  const transcript = String(pendingVoiceEvidence.value?.transcript_text || '').trim()
  const content = draftContent || transcript || String(latestUserMessage?.content || '').trim()
  if (!content) {
    notify('先留下一句，再整理成今日记录')
    return
  }
  if (!saveChatDraftToCheckin(content)) {
    notify('草稿没保存成功，请重新登录后再试')
    return
  }
  router.push('/checkin')
}

function messageTrace(message) {
  return Array.isArray(message?.trace) ? message.trace : []
}

function markTaskConfirmed(message, { proposalId, taskId }) {
  message.payload = { ...message.payload, task_proposals: (message.payload?.task_proposals || []).map(item => item.proposal_id === proposalId ? { ...item, confirmed_task_id: taskId } : item) }
  notify('已加入安排')
}

function toggleTrace(id) {
  openTraceId.value = openTraceId.value === id ? '' : id
}

const checkupRiskTitle = computed(() => {
  const risk = checkupResult.value?.risk_level
  const map = {
    severe: '风险偏高 · 建议尽快关注',
    high: '风险偏高 · 建议尽快关注',
    medium: '有一定波动 · 建议近期关注',
    low: '整体平稳',
    monitor: '整体平稳',
  }
  return map[risk] || '巡查完成'
})

const checkupActions = computed(() => {
  const raw = checkupResult.value?.recommended_actions
  return Array.isArray(raw) ? raw.slice(0, 4) : []
})

const swarmTotalTime = computed(() => {
  const total = (swarmResult.value || []).reduce((sum, step) => sum + (Number(step?.duration_ms) || 0), 0)
  return Math.round(total)
})

async function runCheckup() {
  if (runningCheckup.value) return
  const scope = captureChatScope()
  runningCheckup.value = true
  try {
    const resolvedSessionId = experienceMode.value.isDemoMode && !realAgentDemo.value
      ? ('demo-' + Date.now())
      : await ensureAgentSession()
    notify('亲健正在主动巡查这段关系...')
    assertChatScope(scope)
    const result = await api.runAgentCheckup(resolvedSessionId)
    assertChatScope(scope)
    checkupResult.value = {
      report: result?.report || '本次巡查完成。',
      health: result?.health ?? null,
      risk_level: result?.risk_level || 'monitor',
      risk_reason: result?.risk_reason || '',
      recommended_actions: Array.isArray(result?.recommended_actions) ? result.recommended_actions : [],
      urgency: result?.urgency || 'monitor',
      generated_at: result?.generated_at || null,
    }
    scrollMessagesToBottom()
  } catch (error) {
    notify(error.message || '这次巡查没有完成，请稍后再试')
  } finally {
    runningCheckup.value = false
  }
}

function swarmStatusLabel(step) {
  const map = { ok: '完成', skip: '跳过', error: '失败', fallback: '兜底' }
  return map[step?.status] || '完成'
}

async function runCollaboration() {
  if (collaborating.value) return
  const scope = captureChatScope()
  const content = String(draft.value || '').trim()
  if (!content) {
    notify('先写一句，再让智能体团队协作。')
    return
  }
  collaborating.value = true
  try {
    const resolvedSessionId = experienceMode.value.isDemoMode && !realAgentDemo.value
      ? ('demo-' + Date.now())
      : await ensureAgentSession()
    assertChatScope(scope)
    const result = await api.collaborateWithAgent(resolvedSessionId, {
      content,
      surface: 'chat',
      multi_agent: true,
    })
    assertChatScope(scope)
    swarmResult.value = Array.isArray(result?.swarm) ? result.swarm : []
    messages.value.push(normalizeMessage({
      id: result?.message_id || `local-swarm-${Date.now()}`,
      role: 'assistant',
      content: result?.reply || '智能体团队完成了协作。',
      payload: { surface: 'chat', multi_agent: true, task_proposals: result?.task_proposals || [] },
      trace: Array.isArray(result?.trace) ? result.trace : [],
    }))
    draft.value = ''
    scrollMessagesToBottom()
  } catch (error) {
    notify(error.message || '这是一个多智能体的协作，这次没完成，请稍后再试')
  } finally {
    collaborating.value = false
  }
}

watch(
  () => messages.value.length,
  () => {
    if (messages.value.length) scrollMessagesToBottom()
  }
)

watch(autoSendVoice, (value) => {
  const nextMode = value ? 'auto' : 'manual'
  if (voicePreferences.sending !== nextMode) {
    voicePreferences.sending = nextMode
    persistVoicePreferences()
  }
})

watch(
  () => [activePairId.value, userStore.token, userStore.me?.id],
  async () => {
    chatRevision++
    pendingSessionRequest = null
    sending.value = false
    sendError.value = ''
    sessionId.value = ''
    sessionExpiresAt.value = ''
    startingNewTopic.value = false
    draft.value = ''
    messages.value = []
    pendingVoiceEvidence.value = null
    checkupResult.value = null
    swarmResult.value = null
    runningCheckup.value = false
    collaborating.value = false
    voiceController.value?.cleanup?.()
    cleanupVoiceState()

    await loadInitialSession()
  },
  { flush: 'sync' }
)

onMounted(() => {
  loadInitialSession()
})

onBeforeUnmount(() => {
  chatDisposed = true
  voiceController.value?.cleanup?.()
  cleanupVoiceState()
})
</script>

<style scoped>
.chat-waiting { display: flex; align-items: center; gap: 9px; padding: 10px 14px; color: var(--ink-soft); font-size: 13px; }
.chat-spinner { display: inline-block; width: 15px; height: 15px; flex-shrink: 0; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: chat-turn 0.85s linear infinite; }
.chat-send-error { margin: 2px 14px; color: #ac4934; font-size: 13px; }
@keyframes chat-turn { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .chat-spinner { animation-duration: 2.5s; } }
.chat-msg__reference { color: var(--ink-soft); font-size: 13px; margin-top: 10px; }
.chat-msg__reference summary { cursor: pointer; }
.chat-msg__reference p { white-space: pre-wrap; max-height: 180px; overflow: auto; }
.btn-regenerate {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-primary-600, #d97706);
  font-weight: 500;
}
.is-spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-msg__refinements { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.chat-msg__operations { padding: 0; list-style: none; font-size: 13px; display: grid; gap: 8px; }
.chat-msg__operations li { display: grid; gap: 3px; }
.chat-msg__operations span { color: var(--ink-soft); }

/* 主容器：视口自适应高度 */
.chat-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: calc(100dvh - var(--header-height, 58px) - 20px);
  min-height: 420px;
  box-sizing: border-box;
}

#app-shell.has-tabbar .chat-page {
  height: calc(100dvh - var(--header-height, 58px) - var(--tabbar-height, 58px) - env(safe-area-inset-bottom, 0px) - 16px);
}

.chat-page--embedded {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  gap: 8px;
}

.chat-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.chat-head__title-group h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.25;
}

.chat-head__title-group .eyebrow {
  margin-bottom: 2px;
  font-size: 12px;
}

.chat-head__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.chat-shell {
  flex: 1 1 0%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px;
  border: 1px solid var(--border-strong);
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(215, 104, 72, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(249, 244, 238, 0.9));
  box-shadow: 0 16px 34px rgba(56, 42, 30, 0.05);
  overflow: hidden;
}

/* 顶部轻量工具栏 */
.chat-shell__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.chat-shell__mode {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.chat-shell__privacy {
  color: var(--ink-soft);
  font-size: 12px;
  margin: 0;
}

.voice-preference-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid rgba(189, 75, 53, 0.18);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.88);
  color: var(--ink);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(56, 42, 30, 0.04);
  transition: all 0.15s ease;
}

.voice-preference-trigger svg {
  color: var(--seal);
}

.voice-preference-trigger strong {
  color: var(--seal-deep);
  font-size: 11px;
}

.voice-preference-trigger__short {
  display: none;
}

.voice-preference-trigger:hover {
  border-color: rgba(189, 75, 53, 0.3);
  background: rgba(255, 250, 246, 0.96);
}

.voice-preference-panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 18px;
  background: rgba(255, 253, 250, 0.92);
  flex-shrink: 0;
}

.voice-preference-panel__group {
  display: grid;
  gap: 6px;
}

.voice-preference-panel__group > span {
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 700;
}

.voice-preference-panel__options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.voice-preference-option {
  padding: 5px 9px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.75);
  color: var(--ink);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.voice-preference-option.active {
  border-color: rgba(189, 75, 53, 0.25);
  background: var(--seal-soft);
  color: var(--seal-deep);
  font-weight: 800;
}

.chat-live-card,
.chat-pending-card {
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 18px;
  background: rgba(255, 251, 247, 0.9);
  padding: 12px 14px;
  display: grid;
  gap: 6px;
  flex-shrink: 0;
}

.chat-live-card strong,
.chat-pending-card strong {
  color: #17385e;
  font-family: var(--font-serif);
  font-size: 16px;
}

.chat-live-card p,
.chat-pending-card__transcript,
.chat-msg__text,
.chat-msg__transcript,
.voice-insight-card p {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chat-pending-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.chat-audio {
  width: 100%;
}

/* 消息列表保留历史滚动，独立页面另提供充足的阅读高度。 */
.chat-list {
  flex: 1 1 0%;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 20px;
  background: rgba(255, 251, 247, 0.85);
  scrollbar-width: thin;
}

.chat-msg {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.chat-msg--user {
  flex-direction: row-reverse;
}

.chat-msg__avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid rgba(67, 98, 115, 0.22);
  border-radius: 14px;
  background: var(--moss-soft);
  color: var(--moss-deep);
  font-size: 12px;
  font-weight: 700;
}

.chat-msg--user .chat-msg__avatar {
  border-color: rgba(189, 75, 53, 0.28);
  background: var(--seal-soft);
  color: var(--seal-deep);
}

.chat-msg__bubble {
  max-width: min(72ch, 80%);
  padding: 12px 15px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 253, 250, 0.94);
  display: grid;
  gap: 8px;
}

.chat-msg--user .chat-msg__bubble {
  border-color: rgba(189, 75, 53, 0.22);
  background: rgba(243, 216, 208, 0.55);
}

.chat-msg--error .chat-msg__bubble {
  border-color: rgba(189, 75, 53, 0.4);
  background: rgba(253, 235, 230, 0.9);
}

.chat-msg__error-hint {
  margin: 2px 0 0;
  color: #ac4934;
  font-size: 12px;
}

.chat-msg__trace-toggle {
  border: none;
  background: none;
  padding: 0;
  color: var(--seal-deep);
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  text-decoration: underline;
  cursor: pointer;
}

/* 语音线索与证据卡片 */
.chat-msg__evidence {
  padding-top: 10px;
  border-top: 1px dashed rgba(68, 52, 40, 0.12);
  display: grid;
  gap: 8px;
}

.voice-insight-card {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(78, 116, 91, 0.18);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(235, 242, 232, 0.82), rgba(255, 253, 250, 0.88));
}

.voice-insight-card__body {
  display: grid;
  gap: 6px;
}

.voice-insight-card__body > span,
.voice-insight-card--muted > span {
  color: var(--moss-deep);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.voice-insight-card p {
  color: var(--ink-soft);
  font-size: 13px;
  margin: 0;
}

.voice-insight-tags,
.voice-insight-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.voice-insight-tags strong {
  padding: 5px 9px;
  border: 1px solid rgba(189, 75, 53, 0.2);
  border-radius: 999px;
  background: rgba(255, 246, 241, 0.92);
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 14px;
}

.voice-insight-meta span {
  padding: 4px 7px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.74);
  color: var(--ink-soft);
  font-size: 11px;
  font-weight: 700;
}

.voice-insight-card--muted {
  border-style: dashed;
  background: rgba(255, 253, 250, 0.62);
}

.chat-checkup-card,
.chat-swarm-card {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 18px;
}

.chat-checkup-card {
  border: 1px solid rgba(189, 75, 53, 0.25);
  background: linear-gradient(135deg, rgba(243, 216, 208, 0.42), rgba(255, 253, 250, 0.9));
}

.chat-swarm-card {
  border: 1px solid rgba(78, 116, 91, 0.24);
  background: linear-gradient(135deg, rgba(235, 242, 232, 0.5), rgba(255, 253, 250, 0.92));
}

.chat-checkup-card__head,
.chat-swarm-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.chat-swarm-card__roles {
  display: grid;
  gap: 8px;
}

.chat-swarm-card__role {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-left: 3px solid rgba(78, 116, 91, 0.4);
  border-radius: 12px;
  background: rgba(255, 253, 250, 0.8);
}

.chat-swarm-card__role-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-swarm-card__role-index {
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--moss-deep);
  color: #fff;
  font-size: 10px;
  font-weight: 800;
}

.chat-swarm-card__role-name {
  color: var(--moss-deep);
  font-size: 14px;
  font-weight: 800;
}

.chat-swarm-card__role-status {
  color: var(--ink-soft);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(78, 116, 91, 0.1);
}

.chat-swarm-card__role-time {
  color: var(--ink-soft);
  font-size: 11px;
  margin-left: auto;
}

/* 快捷提问栏：吸附在输入框上方，横向平滑滚动 */
.chat-suggestions-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px dashed rgba(68, 52, 40, 0.16);
  flex-shrink: 0;
}

.chat-suggestions-bar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.chat-suggestions-bar__title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.chat-suggestions-bar__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--seal, #d76848);
  flex-shrink: 0;
}

.chat-suggestions-bar__title {
  font-weight: 800;
  color: var(--ink);
  white-space: nowrap;
}

.chat-suggestions-bar__scenario {
  color: var(--ink-soft);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-suggestions-bar__hint {
  color: var(--ink-soft);
  font-size: 11px;
  flex-shrink: 0;
}

.chat-suggestions-bar__list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: thin;
  -webkit-overflow-scrolling: touch;
}

.chat-suggestion-chip {
  flex-shrink: 0;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(68, 52, 40, 0.12);
  background: #ffffff;
  color: var(--ink);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  max-width: 360px;
  text-overflow: ellipsis;
  overflow: hidden;
}

.chat-suggestion-chip:hover:not(:disabled) {
  border-color: var(--seal);
  background: rgba(215, 104, 72, 0.08);
  transform: translateY(-1px);
}

/* 底部输入框区域 */
.chat-composer {
  flex-shrink: 0;
  padding: 10px 14px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 20px;
  background: rgba(255, 251, 247, 0.94);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-composer__field {
  margin: 0;
}

.chat-composer__input {
  width: 100%;
  box-sizing: border-box;
  min-height: 50px;
  max-height: 110px;
  font-size: 15px;
  line-height: 1.55;
  background: rgba(255, 254, 251, 0.95);
  resize: vertical;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid rgba(68, 52, 40, 0.12);
}

.chat-composer__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-send {
  min-width: 72px;
}

/* 独立聊天页允许整页向下滚动，不让推荐区和输入框挤压消息。 */
@media (min-width: 601px) {
  .chat-page:not(.chat-page--embedded),
  #app-shell.has-tabbar .chat-page:not(.chat-page--embedded) {
    height: auto;
    min-height: calc(100dvh - var(--header-height, 58px) - 20px);
    padding-bottom: 28px;
  }

  .chat-page:not(.chat-page--embedded) .chat-shell {
    flex: 0 0 auto;
  }

  .chat-page:not(.chat-page--embedded) .chat-list {
    flex: 0 0 auto;
    height: clamp(480px, 65dvh, 900px);
    box-sizing: border-box;
  }
}

/* 响应式断点优化 */
@media (max-width: 900px) {
  .chat-page {
    width: min(100% - 20px, var(--content-max));
  }

  .voice-preference-panel {
    grid-template-columns: 1fr;
  }

  .chat-msg__bubble {
    max-width: calc(100% - 44px);
  }
}

@media (max-width: 600px) {
  .chat-page {
    width: 100%;
    padding: 0 8px 6px;
    height: calc(100dvh - var(--header-height, 58px) - 10px);
    gap: 6px;
  }

  #app-shell.has-tabbar .chat-page {
    height: calc(100dvh - var(--header-height, 58px) - var(--tabbar-height, 58px) - env(safe-area-inset-bottom, 0px) - 10px);
  }

  .chat-head {
    gap: 6px;
    margin-bottom: 2px;
  }

  .chat-head__title-group .eyebrow {
    display: none;
  }

  .chat-head__title-group h2 {
    font-size: 16px;
  }

  .chat-head__actions {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }

  .chat-head__actions .btn {
    flex-shrink: 0;
    white-space: nowrap;
    padding: 4px 8px;
    font-size: 12px;
  }

  .chat-shell {
    padding: 8px 10px;
    border-radius: 16px;
    gap: 6px;
  }

  .chat-shell__toolbar {
    gap: 6px;
  }

  .chat-shell__privacy {
    font-size: 11px;
  }

  .chat-list {
    padding: 10px;
    border-radius: 14px;
    gap: 10px;
  }

  .chat-suggestions-bar {
    padding: 6px 10px;
    border-radius: 12px;
    gap: 4px;
  }

  .chat-suggestion-chip {
    padding: 4px 10px;
    font-size: 11px;
    max-width: 260px;
  }

  .chat-composer {
    padding: 6px 8px;
    border-radius: 14px;
    gap: 5px;
  }

  .chat-composer__input {
    min-height: 40px;
    max-height: 80px;
    font-size: 13px;
    padding: 6px 8px;
  }

  .chat-composer__actions {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .chat-composer__actions .btn {
    padding: 4px 8px;
    font-size: 12px;
    white-space: nowrap;
  }

  .voice-preference-trigger {
    padding: 3px 8px;
    font-size: 11px;
  }

  .voice-preference-trigger__full {
    display: none;
  }

  .voice-preference-trigger__short {
    display: inline;
  }
}
</style>

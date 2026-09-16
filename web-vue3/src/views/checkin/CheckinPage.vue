<template>
  <div class="checkin-page">
    <div class="page-head checkin-head">
      <p class="eyebrow">关系记录</p>
      <h2>把今天想说的一句话先留住</h2>
    </div>

    <div class="segmented checkin-mode">
      <button type="button" :class="{ active: mode === 'form' }" @click="switchMode('form')">手写记录</button>
      <button type="button" :class="{ active: mode === 'voice' }" @click="switchMode('voice')">陪伴整理</button>
    </div>

    <form v-if="mode === 'form'" class="checkin-workbench" @submit.prevent="handleSubmit">
      <section class="record-editor">
        <div class="record-editor__head">
          <div>
            <p class="eyebrow">今日记录</p>
            <h3>想说点什么？</h3>
          </div>
          <label v-if="availableCheckinPairs.length" class="checkin-pair-picker" aria-label="记录对象">
            <select :value="activePairId" :disabled="availableCheckinPairs.length < 2" @change="switchCheckinPair">
              <option v-for="pair in availableCheckinPairs" :key="pair.id" :value="pair.id">
                {{ pairNicknameLabel(pair) }}
              </option>
            </select>
          </label>
        </div>

        <div class="field record-content-field">
          <span>今天发生了什么？</span>
          <div
            class="record-input-shell"
            :class="{
              'is-listening': dictationState === 'listening',
              'is-finalizing': dictationState === 'finalizing',
              'has-dictation-draft': hasDictationDraft,
              'has-error': dictationState === 'error',
            }"
          >
            <textarea
              v-model="form.content"
              class="input input-textarea record-textarea"
              placeholder="例如：她说“你根本没懂我为什么会难受”，我第一反应是想解释。"
            ></textarea>
            <div class="dictation-dock" aria-live="polite">
              <div v-if="dictationPreview || dictationStatusText" class="dictation-status">
                <span v-if="dictationState === 'listening'" class="dictation-pulse" aria-hidden="true"></span>
                <span v-else class="dictation-dot" aria-hidden="true"></span>
                <p>{{ dictationPreview || dictationStatusText }}</p>
              </div>
              <div class="dictation-actions" aria-label="语音转文字">
                <button
                  v-if="dictationState === 'listening' || dictationState === 'finalizing'"
                  class="dictation-icon-button dictation-icon-button--stop"
                  type="button"
                  :disabled="dictationState === 'finalizing'"
                  aria-label="停止转写"
                  title="停止转写"
                  @click="stopDictation"
                >
                  <Loader2 v-if="dictationState === 'finalizing'" :size="18" class="spin-icon" />
                  <StopCircle v-else :size="19" />
                </button>
                <button
                  v-else
                  class="dictation-icon-button"
                  type="button"
                  aria-label="语音转文字"
                  title="语音转文字"
                  @click="handleDictationMicClick"
                  @pointerdown="handleDictationPointerDown"
                  @pointerup="handleDictationPointerUp"
                  @pointercancel="handleDictationPointerCancel"
                  @pointerleave="handleDictationPointerLeave"
                >
                  <Mic :size="19" />
                </button>
                <button
                  v-if="hasDictationDraft"
                  class="dictation-icon-button dictation-icon-button--send"
                  type="button"
                  aria-label="填入正文"
                  title="填入正文"
                  @click="commitDictationPreview"
                >
                  <SendHorizontal :size="18" />
                </button>
                <button
                  v-if="dictationState !== 'idle' || hasDictationDraft"
                  class="dictation-icon-button dictation-icon-button--ghost"
                  type="button"
                  aria-label="取消转写"
                  title="取消转写"
                  @click="cancelDictation"
                >
                  <X :size="18" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="field mood-field">
          <div class="mood-field__head">
            <span>此刻心情</span>
            <div class="mood-field__actions">
              <button
                v-if="hiddenDefaultMoods.length"
                class="btn btn-ghost btn-sm mood-field__action"
                type="button"
                :disabled="savingMoodPreset"
                @click="restoreDefaultMoods"
              >
                恢复默认
              </button>
              <button
                class="btn btn-ghost btn-sm mood-field__action"
                type="button"
                @click="managingMoodLibrary = !managingMoodLibrary"
              >
                {{ managingMoodLibrary ? '完成管理' : '管理心情' }}
              </button>
            </div>
          </div>
          <div v-if="visibleDefaultMoods.length" class="tag-cloud mood-tags">
            <div
              v-for="mood in visibleDefaultMoods"
              :key="mood"
              class="mood-tag-item"
              :class="{ 'mood-tag-item--managing': managingMoodLibrary }"
            >
              <button
                class="tag"
                :class="{ active: form.moods.includes(mood) }"
                type="button"
                @click="toggleMood(mood)"
              >
                {{ mood }}
              </button>
              <button
                v-if="managingMoodLibrary"
                class="mood-tag-item__remove"
                type="button"
                :aria-label="`隐藏默认心情 ${mood}`"
                :disabled="savingMoodPreset"
                @click.stop="hideDefaultMood(mood)"
              >
                <X :size="12" />
              </button>
            </div>
          </div>
          <p v-else class="mood-field__empty">默认心情已隐藏。</p>

          <div v-if="commonMoodPresets.length" class="mood-presets">
            <span>我的常用心情</span>
            <div class="tag-cloud mood-tags mood-tags--presets">
              <div
                v-for="mood in commonMoodPresets"
                :key="mood"
                class="mood-tag-item"
                :class="{ 'mood-tag-item--managing': managingMoodLibrary }"
              >
                <button
                  class="tag"
                  :class="{ active: form.moods.includes(mood) }"
                  type="button"
                  @click="toggleMood(mood)"
                >
                  {{ mood }}
                </button>
                <button
                  v-if="managingMoodLibrary"
                  class="mood-tag-item__remove"
                  type="button"
                  :aria-label="`删除常用心情 ${mood}`"
                  :disabled="savingMoodPreset"
                  @click.stop="removeCustomMoodPreset(mood)"
                >
                  <X :size="12" />
                </button>
              </div>
            </div>
          </div>

          <label class="mood-custom-field" :class="{ active: hasCustomMood }">
            <span>自定义补充</span>
            <div class="mood-custom-field__row">
              <input
                v-model="form.customMood"
                class="mood-custom-field__input"
                type="text"
                maxlength="24"
                placeholder="比如：失落、心虚、释然"
                @keydown.enter.prevent
              />
              <button
                class="btn btn-ghost btn-sm mood-custom-field__save"
                type="button"
                :disabled="!canSaveCustomMood || savingMoodPreset"
                @click="saveCustomMoodPreset"
              >
                {{ moodSaveButtonLabel }}
              </button>
            </div>
          </label>
        </div>
      </section>

      <aside class="record-aside">
        <details class="context-panel" open>
          <summary>补充上下文</summary>
          <div class="form-stack">
            <div class="field">
              <span style="display:flex;align-items:center;gap:6px;"><Smile :size="16" />今天整体感受</span>
              <div class="option-grid context-score-grid">
                <button v-for="n in 10" :key="n" class="select-card context-score-button" type="button" :class="{ active: form.moodScore === n }" @click="form.moodScore = n">
                  {{ n }}
                </button>
              </div>
            </div>
            <div class="field" style="margin-top: 12px;">
              <span style="display:flex;align-items:center;gap:6px;"><Activity :size="16" />互动频率</span>
              <div class="option-grid context-score-grid">
                <button v-for="n in 10" :key="n" class="select-card context-score-button" type="button" :class="{ active: form.interactionFreq === n }" @click="form.interactionFreq = n">
                  {{ n }}
                </button>
              </div>
            </div>
            <div class="field" style="margin-top: 4px;">
              <span style="display:flex;align-items:center;gap:6px;"><UserCheck :size="16" />谁先开口</span>
              <div class="option-grid option-grid--three">
                <button class="select-card" :class="{ active: form.initiative === 'me' }" type="button" @click="form.initiative = 'me'">我</button>
                <button class="select-card" :class="{ active: form.initiative === 'partner' }" type="button" @click="form.initiative = 'partner'">对方</button>
                <button class="select-card" :class="{ active: form.initiative === 'equal' }" type="button" @click="form.initiative = 'equal'">差不多</button>
              </div>
            </div>
            <div class="field">
              <span>有没有深聊</span>
              <div class="option-grid option-grid--two">
                <button class="select-card" :class="{ active: form.deepConversation === true }" type="button" @click="form.deepConversation = true">有</button>
                <button class="select-card" :class="{ active: form.deepConversation === false }" type="button" @click="form.deepConversation = false">没有</button>
              </div>
            </div>
            <div class="field">
              <span>之前的约定</span>
              <div class="option-grid option-grid--two">
                <button class="select-card" :class="{ active: form.taskCompleted === true }" type="button" @click="form.taskCompleted = true">做到了</button>
                <button class="select-card" :class="{ active: form.taskCompleted === false }" type="button" @click="form.taskCompleted = false">还没</button>
              </div>
            </div>
          </div>
        </details>
      </aside>

      <div class="record-support-grid">
        <details class="attachment-panel">
          <summary>附件</summary>
          <div class="upload-row">
            <button class="btn btn-ghost btn-sm" type="button" @click="imageInput?.click()">添加图片</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="voiceInput?.click()">添加语音</button>
          </div>
          <input ref="imageInput" type="file" accept="image/*" class="hidden" @change="handleImageUpload" />
          <input ref="voiceInput" type="file" accept="audio/*" class="hidden" @change="handleVoiceUpload" />
          <div v-if="imagePreview" class="upload-preview">
            <img :src="imagePreview" alt="已上传图片" />
          </div>
          <div v-if="voiceMeta" class="voice-preview">
            <strong>语音已读取</strong>
            <span>时长 {{ voiceMeta.duration_seconds || '--' }}s · 静音比 {{ voiceMeta.silence_ratio ?? '--' }}</span>
          </div>
          <div v-if="imageFile" class="upload-row">
            <button class="btn btn-ghost btn-sm" type="button" :disabled="imageAnalysisLoading" @click="analyzeAttachedImage()">
              {{ imageAnalysisLoading ? '正在分析图片...' : imageAnalysis ? '重新分析图片' : '分析这张图' }}
            </button>
          </div>
          <article v-if="imageAnalysis" class="image-insight-card">
            <span>图片里更像在发生</span>
            <strong>{{ imageAnalysis.scene_summary }}</strong>
            <p>{{ imageAnalysis.social_signal }}</p>
            <div v-if="imageDisplayMoodTags.length || imageEmotionSummary" class="image-emotion-card">
              <span>重点感受</span>
              <div v-if="imageDisplayMoodTags.length" class="image-emotion-card__tags">
                <strong v-for="tag in imageDisplayMoodTags" :key="tag">{{ tag }}</strong>
              </div>
              <p v-if="imageEmotionSummary">{{ imageEmotionSummary }}</p>
            </div>
            <div class="evidence-strip">
              <span class="evidence-pill">{{ imageAnalysis.risk_level_label }}</span>
              <span class="evidence-pill">{{ imageAnalysis.privacy_sensitivity_label }}</span>
              <span class="evidence-pill">{{ imageStorage?.retention_recommendation_label || '只展示分析结果' }}</span>
            </div>
          </article>
        </details>
      </div>

      <div class="checkin-submit-bar">
        <button type="submit" class="btn btn-primary btn-block" :disabled="!canSubmitManualCheckin">
          {{ submitting ? '保存中...' : '保存记录' }}
        </button>
      </div>
    </form>

    <section v-else class="voice-draft">
      <div class="voice-draft__head">
        <div>
          <p class="eyebrow">对话整理</p>
          <h3>说出来，助手帮你整理成记录</h3>
        </div>
        <label v-if="availableCheckinPairs.length" class="checkin-pair-picker" aria-label="记录对象">
          <select :value="activePairId" :disabled="availableCheckinPairs.length < 2" @change="switchCheckinPair">
            <option v-for="pair in availableCheckinPairs" :key="pair.id" :value="pair.id">
              {{ pairNicknameLabel(pair) }}
            </option>
          </select>
        </label>
      </div>

      <div class="voice-toolbar" aria-live="polite">
        <div>
          <strong>{{ asrActive ? '正在听你说' : asrFinalizing ? '正在整理最后一句' : '可以开始说话了' }}</strong>
          <p v-if="voiceStatus">{{ voiceStatus }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="asrFinalizing" @click="toggleVoiceInput">
          {{ asrActive ? '停止说话' : asrFinalizing ? '整理中...' : '开始说话' }}
        </button>
      </div>

      <div v-if="!messages.length" class="empty-state">心里有什么琐碎或委屈，随时跟我说说，比如“今天下班真的好累呀~”</div>
      <div v-else class="chat-list">
        <div v-for="(msg, i) in messages" :key="i" class="chat-msg" :class="{ 'chat-msg--user': msg.role === 'user' }">
          <div class="chat-msg__avatar">{{ msg.role === 'user' ? '我' : '助' }}</div>
          <div class="chat-msg__bubble">{{ msg.content }}</div>
        </div>
      </div>

      <div class="form-stack voice-input">
        <textarea ref="chatInputEl" v-model="chatInput" class="input input-textarea voice-chat-textarea" placeholder="随手写点心里话，比如：今天工作有点糟心，不过晚上一起吃了碗热汤面，心情好多了~"></textarea>
        <div class="hero-actions">
          <button class="btn btn-primary" type="button" :disabled="agentSending || asrFinalizing" @click="sendChat">
            {{ agentSending ? '发送中...' : '发给助手' }}
          </button>
          <button class="btn btn-ghost" type="button" @click="replayAgentReply">朗读上一条</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { Activity, Loader2, Mic, SendHorizontal, Smile, StopCircle, UserCheck, X } from 'lucide-vue-next'
import { computed, inject, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { useCheckinStore } from '@/stores/checkin'
import { api } from '@/api'
import { consumeChatDraftToCheckin } from '@/utils/checkinDraftBridge'
import { getManualCheckinValidation } from '@/utils/checkinForm'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { createBackendRealtimeAsr, startBrowserSpeech } from '@/utils/realtimeVoice'
import { relationshipTypeLabel } from '@/utils/displayText'

const userStore = useUserStore()
const checkinStore = useCheckinStore()
const showToast = inject('showToast')

const mode = ref('form')
const submitting = ref(false)
const uploading = ref(false)
const agentSending = ref(false)
const moods = ['开心', '平静', '感动', '期待', '焦虑', '委屈', '生气', '疲惫']

const imageInput = ref(null)
const voiceInput = ref(null)
const chatInputEl = ref(null)
const imageFile = ref(null)
const imagePreview = ref('')
const imageMeta = ref(null)
const imageAnalysisLoading = ref(false)
const voiceFile = ref(null)
const voiceMeta = ref(null)
const messages = ref([])
const chatInput = ref('')
const agentSessionId = ref('')
const lastAgentReply = ref('')
const asrActive = ref(false)
const asrFinalizing = ref(false)
const voiceStatus = ref('')
const voiceController = ref(null)
const savingMoodPreset = ref(false)
const managingMoodLibrary = ref(false)
const dictationController = ref(null)
const dictationActive = ref(false)
const dictationFinalizing = ref(false)
const dictationStatus = ref('')
const dictationPreview = ref('')
const dictationError = ref('')
const dictationState = ref('idle')

const form = reactive({
  content: '',
  moods: [],
  customMood: '',
  moodScore: null,
  interactionFreq: null,
  initiative: '',
  deepConversation: null,
  taskCompleted: null,
})

const MAX_CUSTOM_MOOD_PRESETS = 12
const DICTATION_LONG_PRESS_MS = 350
let voiceFallbackTried = false
let dictationFallbackTried = false
let dictationLongPressTimer = null
let dictationPointerDown = false
let dictationLongPressStarted = false
let suppressNextDictationClick = false

const imageAnalysis = computed(() => imageMeta.value?.analysis || null)
const imageStorage = computed(() => imageMeta.value?.storage || null)
const imageDisplayMoodTags = computed(() => {
  const analysis = imageAnalysis.value || {}
  const userFacing = analysis.user_facing || {}
  const profile = analysis.emotion_profile || {}
  return uniqueStrings(
    firstNonEmptyArray(
      userFacing.display_mood_tags,
      analysis.display_mood_tags,
      profile.display_mood_tags,
      analysis.mood_tags,
      [
        analysis.primary_mood,
        ...(Array.isArray(analysis.secondary_moods) ? analysis.secondary_moods : []),
      ],
      profile.all_mood_tags,
    ),
    3,
  )
})
const imageEmotionSummary = computed(() => {
  const analysis = imageAnalysis.value || {}
  return String(
    analysis.user_facing?.blend_summary
      || analysis.emotion_blend_summary
      || analysis.emotion_profile?.blend_summary
      || '',
  ).trim()
})
const manualCheckinValidation = computed(() => getManualCheckinValidation({
  content: form.content,
  imageAnalysisSummary: imageAnalysis.value?.scene_summary,
  moodScore: form.moodScore,
  interactionFreq: form.interactionFreq,
  initiative: form.initiative,
  deepConversation: form.deepConversation,
  taskCompleted: form.taskCompleted,
}))
const normalizedManualContent = computed(() => manualCheckinValidation.value.normalizedManualContent)
const missingBackgroundFields = computed(() => manualCheckinValidation.value.missingBackgroundFields)
const isBackgroundComplete = computed(() => manualCheckinValidation.value.isBackgroundComplete)
const canSubmitManualCheckin = computed(
  () => Boolean(normalizedManualContent.value) && isBackgroundComplete.value && !submitting.value && !uploading.value,
)
const commonMoodPresets = computed(() => {
  const source = userStore.me?.custom_mood_presets
  return Array.isArray(source)
    ? source.map((item) => normalizeCustomMood(item)).filter(Boolean)
    : []
})
const hiddenDefaultMoods = computed(() => {
  const source = userStore.me?.hidden_default_moods
  return Array.isArray(source)
    ? source
      .map((item) => normalizeCustomMood(item))
      .filter((item) => moods.includes(item))
    : []
})
const visibleDefaultMoods = computed(() => (
  moods.filter((mood) => !hiddenDefaultMoods.value.includes(mood))
))
const hasCustomMood = computed(() => Boolean(normalizeCustomMood(form.customMood)))
const customMoodValue = computed(() => normalizeCustomMood(form.customMood))
const customMoodAlreadySaved = computed(() => commonMoodPresets.value.includes(customMoodValue.value))
const customMoodIsBuiltIn = computed(() => moods.includes(customMoodValue.value))
const canSaveCustomMood = computed(() => (
  Boolean(customMoodValue.value)
  && !customMoodAlreadySaved.value
  && !customMoodIsBuiltIn.value
))
const moodSaveButtonLabel = computed(() => {
  if (savingMoodPreset.value) return '保存中...'
  if (customMoodAlreadySaved.value) return '已保存'
  if (customMoodIsBuiltIn.value && customMoodValue.value) return '默认已有'
  return '保存常用'
})
const selectedMoodTags = computed(() => {
  const customMood = normalizeCustomMood(form.customMood)
  return Array.from(new Set([
    ...form.moods.map((item) => String(item || '').trim()),
    customMood,
  ].filter(Boolean)))
})
const activePairId = computed(() => userStore.activePairId || null)
const availableCheckinPairs = computed(() =>
  (userStore.pairs || []).filter((pair) => pair?.status === 'active' && pair?.id)
)
const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const hasDictationDraft = computed(() => Boolean(normalizeDictationText(dictationPreview.value)))
const dictationStatusText = computed(() => {
  if (dictationState.value === 'error') return dictationError.value || '没听清'
  if (dictationState.value === 'finalizing') return '整理中'
  if (dictationState.value === 'listening') return '正在听'
  if (hasDictationDraft.value) return '已转好'
  return dictationStatus.value
})

function pairDisplayName(pair) {
  return String(
    pair?.custom_partner_nickname
      || pair?.partner_nickname
      || pair?.partner_email
      || pair?.partner_phone
      || '对方',
  ).trim()
}

function pairOptionLabel(pair) {
  return `${relationshipTypeLabel(pair?.type)} · ${pairDisplayName(pair)}`
}

function pairNicknameLabel(pair) {
  return pairDisplayName(pair)
}

async function switchCheckinPair(event) {
  const nextPairId = String(event?.target?.value || '').trim()
  if (!nextPairId || nextPairId === userStore.activePairId) return
  cancelDictation()
  await userStore.switchPair(nextPairId)
  agentSessionId.value = ''
  messages.value = []
  lastAgentReply.value = ''
}

function notify(message) {
  if (message) showToast?.(message)
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
  return candidates.find((items) => Array.isArray(items) && items.some((item) => String(item || '').trim())) || []
}

function normalizeCustomMood(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/[，、；;]+$/u, '')
    .trim()
    .slice(0, 24)
}

function normalizeDictationText(value) {
  return String(value || '').trim()
}

function compactDictationStatus(value) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (/整理|最后/.test(text)) return '整理中'
  if (/打开|开启|听|转写|识别|浏览器|麦克风/.test(text)) return '正在听'
  return text.length > 8 ? '正在听' : text
}

function setDictationState(nextState) {
  dictationState.value = nextState
  dictationActive.value = nextState === 'listening'
  dictationFinalizing.value = nextState === 'finalizing'
}

function clearDictationLongPressTimer() {
  if (dictationLongPressTimer) {
    window.clearTimeout(dictationLongPressTimer)
    dictationLongPressTimer = null
  }
}

function revokeImagePreview() {
  if (imagePreview.value?.startsWith?.('blob:')) URL.revokeObjectURL(imagePreview.value)
}

function switchMode(nextMode) {
  if (nextMode !== 'voice') stopVoiceInput({ discard: true })
  if (nextMode !== 'form') cancelDictation()
  mode.value = nextMode
  if (nextMode === 'voice') nextTick(() => chatInputEl.value?.focus())
}

function toggleMood(mood) {
  const idx = form.moods.indexOf(mood)
  if (idx >= 0) form.moods.splice(idx, 1)
  else form.moods.push(mood)
}

async function persistMoodPreferenceUpdate(payload, successMessage, failureMessage) {
  if (experienceMode.value.isDemoMode) {
    notify('样例记录不写入账号')
    return false
  }
  savingMoodPreset.value = true
  try {
    await userStore.updateMe(payload)
    if (successMessage) notify(successMessage)
    return true
  } catch (error) {
    notify(error.message || failureMessage)
    return false
  } finally {
    savingMoodPreset.value = false
  }
}

async function saveCustomMoodPreset() {
  const mood = customMoodValue.value
  if (!mood) {
    notify('先写一个你想保存的心情')
    return
  }
  if (customMoodIsBuiltIn.value) {
    notify('这个心情已经在默认标签里了')
    return
  }
  if (customMoodAlreadySaved.value) {
    notify('这个心情已经保存过了')
    return
  }

  const merged = [...commonMoodPresets.value.filter((item) => item !== mood), mood]
  const trimmed = merged.slice(-MAX_CUSTOM_MOOD_PRESETS)
  const replacedOldest = merged.length > MAX_CUSTOM_MOOD_PRESETS
  await persistMoodPreferenceUpdate(
    { custom_mood_presets: trimmed },
    replacedOldest ? '已保存到常用心情，并替换了最早的一项' : '已保存到常用心情',
      '常用心情没保存上，请稍后再试',
  )
}

async function removeCustomMoodPreset(mood) {
  const nextPresets = commonMoodPresets.value.filter((item) => item !== mood)
  if (nextPresets.length === commonMoodPresets.value.length) return

  const retainedInDraft = form.moods.includes(mood)
  await persistMoodPreferenceUpdate(
    { custom_mood_presets: nextPresets },
    retainedInDraft
      ? `已删掉常用心情“${mood}”，当前记录里仍保留这个选择`
      : `已删掉常用心情“${mood}”`,
      '常用心情没删掉，请稍后再试',
  )
}

async function hideDefaultMood(mood) {
  if (!moods.includes(mood)) return
  const nextHidden = [...hiddenDefaultMoods.value.filter((item) => item !== mood), mood]
  const retainedInDraft = form.moods.includes(mood)
  await persistMoodPreferenceUpdate(
    { hidden_default_moods: nextHidden },
    retainedInDraft
      ? `已从默认标签里移除“${mood}”，当前记录里仍保留这个选择`
      : `已从默认标签里移除“${mood}”`,
      '默认心情没更新，请稍后再试',
  )
}

async function restoreDefaultMoods() {
  if (!hiddenDefaultMoods.value.length) {
    notify('默认心情已经是完整的')
    return
  }

  await persistMoodPreferenceUpdate(
    { hidden_default_moods: [] },
    '默认心情已恢复',
      '默认心情没恢复，请稍后再试',
  )
}

function mergeVoiceTextIntoContent(text) {
  const normalized = String(text || '').trim()
  if (!normalized) return
  if (!form.content.trim()) {
    form.content = normalized
    return
  }
  if (!form.content.includes(normalized)) {
    form.content = `${form.content.trim()}\n${normalized}`
  }
}

function cleanupDictationState(status = '', options = {}) {
  const { keepPreview = false, state = 'idle' } = options
  setDictationState(state)
  dictationStatus.value = status
  if (!keepPreview) dictationPreview.value = ''
  if (state !== 'error') dictationError.value = ''
  dictationController.value = null
  clearDictationLongPressTimer()
  dictationPointerDown = false
  dictationLongPressStarted = false
}

function stopDictation({ discard = false } = {}) {
  clearDictationLongPressTimer()
  if (!dictationController.value) {
    if (discard) cleanupDictationState()
    return
  }
  if (discard) {
    dictationController.value.stop?.({ discard: true })
    cleanupDictationState()
    return
  }
  setDictationState('finalizing')
  dictationStatus.value = '正在整理'
  dictationController.value.stop?.({ discard: false })
}

function cancelDictation() {
  stopDictation({ discard: true })
  cleanupDictationState()
}

function handleDictationError(message) {
  const normalized = String(message || '').trim() || '没听清'
  dictationError.value = normalized
  cleanupDictationState(normalized, { state: 'error' })
  notify(normalized)
}

async function handleDictationFinal(result) {
  const resultText = typeof result === 'string' ? result : result?.text
  const finalText = normalizeDictationText(resultText || dictationPreview.value)
  if (!finalText) {
    handleDictationError('没听清')
    return
  }
  dictationPreview.value = finalText
  dictationStatus.value = '已转好'
  dictationController.value = null
  setDictationState('previewReady')
}

function handleBackendDictationError(message) {
  if (!dictationFallbackTried) {
    dictationFallbackTried = true
    try {
      startBrowserDictation(message)
      return
    } catch {
      // Use the backend error when browser speech is unavailable.
    }
  }
  handleDictationError(message)
}

function startBrowserDictation(reason = '') {
  dictationController.value = startBrowserSpeech({
    reason: '',
    onActive: () => {
      setDictationState('listening')
      dictationError.value = ''
    },
    onStatus: (text) => {
      dictationStatus.value = compactDictationStatus(text)
    },
    onPartial: (text) => {
      if (dictationState.value !== 'listening') return
      dictationPreview.value = text
      dictationStatus.value = '正在听'
    },
    onFinal: handleDictationFinal,
    onError: handleDictationError,
  })
}

async function startDictation() {
  if (dictationState.value === 'listening') {
    stopDictation()
    return
  }
  if (dictationState.value === 'finalizing') {
    notify('正在整理')
    return
  }

  dictationFallbackTried = false
  dictationPreview.value = ''
  dictationError.value = ''
  dictationStatus.value = '打开中'
  setDictationState('finalizing')

  try {
    if (experienceMode.value.isDemoMode) {
      startBrowserDictation()
      return
    }
    if (!experienceMode.value.canUseVoice) {
      throw new Error(featureUnavailableReason('voice', experienceMode.value))
    }
    dictationController.value = createBackendRealtimeAsr({
      getSocketUrl: () => api.buildRealtimeAsrSocketUrl(),
      onActive: () => {
        setDictationState('listening')
        dictationError.value = ''
      },
      onStatus: (text) => {
        dictationStatus.value = compactDictationStatus(text)
      },
      onPartial: (text) => {
        if (dictationState.value !== 'listening') return
        dictationPreview.value = text
        dictationStatus.value = '正在听'
      },
      onFinal: handleDictationFinal,
      onError: handleBackendDictationError,
    })
    await dictationController.value.start()
  } catch (error) {
    if (!experienceMode.value.isDemoMode) {
      try {
        startBrowserDictation(error.message)
        return
      } catch {
        // Fall through to a clear inline error.
      }
    }
    handleDictationError(error.message || '打不开麦克风')
  }
}

function handleDictationMicClick() {
  if (suppressNextDictationClick) {
    suppressNextDictationClick = false
    return
  }
  startDictation()
}

function handleDictationPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return
  if (dictationState.value === 'listening' || dictationState.value === 'finalizing') return
  dictationPointerDown = true
  dictationLongPressStarted = false
  clearDictationLongPressTimer()
  dictationLongPressTimer = window.setTimeout(() => {
    if (!dictationPointerDown) return
    dictationLongPressStarted = true
    suppressNextDictationClick = true
    startDictation()
  }, DICTATION_LONG_PRESS_MS)
}

function handleDictationPointerUp() {
  const shouldStop = dictationLongPressStarted
  clearDictationLongPressTimer()
  dictationPointerDown = false
  dictationLongPressStarted = false
  if (shouldStop) stopDictation()
}

function handleDictationPointerCancel() {
  const shouldCancel = dictationLongPressStarted
  clearDictationLongPressTimer()
  dictationPointerDown = false
  dictationLongPressStarted = false
  if (shouldCancel) cancelDictation()
}

function handleDictationPointerLeave(event) {
  if (event.pointerType !== 'mouse') return
  if (!dictationPointerDown || !dictationLongPressStarted) return
  handleDictationPointerUp()
}

function commitDictationPreview() {
  const text = normalizeDictationText(dictationPreview.value)
  if (!text) {
    notify('没有可填入的文字')
    return
  }
  mergeVoiceTextIntoContent(text)
  cleanupDictationState()
  notify('已放进正文')
}

function buildDeviceMeta() {
  const meta = {}
  if (imageMeta.value) meta.image = imageMeta.value
  if (voiceMeta.value) meta.voice = voiceMeta.value
  return Object.keys(meta).length ? meta : null
}

async function analyzeAttachedImage({ silent = false } = {}) {
  if (!imageFile.value || imageAnalysisLoading.value) return null
  if (experienceMode.value.isDemoMode) {
    if (!silent) notify('样例图片已放好')
    return null
  }
  imageAnalysisLoading.value = true
  try {
    const result = await api.analyzeImage(imageFile.value, {
      context: form.content.trim(),
    })
    imageMeta.value = {
      ...(imageMeta.value || {}),
      analysis: result?.analysis || null,
      storage: result?.storage || null,
      analyzed_at: new Date().toISOString(),
    }
    if (!silent) notify(result?.storage?.label || '图片分析已完成')
    return result
  } catch (error) {
    if (!silent) notify(error.message || '图片分析暂时不可用')
    return null
  } finally {
    imageAnalysisLoading.value = false
  }
}

async function handleImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  revokeImagePreview()
  imageFile.value = file
  imagePreview.value = URL.createObjectURL(file)
  imageMeta.value = {
    original_type: file.type,
    original_size: file.size,
    compressed_size: file.size,
    exif_removed: false,
    analysis: null,
    storage: null,
  }
  await analyzeAttachedImage({ silent: true })
  notify(imageAnalysis.value ? '图片已添加，也已完成图片分析' : '图片已添加，提交前还可以再改')
}

async function handleVoiceUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    voiceFile.value = file
    voiceMeta.value = {
      original_type: file.type,
      original_size: file.size,
      name: file.name,
    }
    notify('语音已添加')
  } catch (error) {
    notify(error.message || '语音没读取出来')
  } finally {
    uploading.value = false
  }
}

async function uploadAttachment(type, file) {
  if (!file) return null
  const result = await api.uploadFile(type, file)
  if (type === 'image') {
    imageMeta.value = {
      ...(imageMeta.value || {}),
      upload: result || null,
    }
  }
  return result?.url || result?.file_url || result?.path || null
}

function resetForm() {
  form.content = ''
  form.moods = []
  form.customMood = ''
  form.moodScore = null
  form.interactionFreq = null
  form.initiative = ''
  form.deepConversation = null
  form.taskCompleted = null
  revokeImagePreview()
  imageFile.value = null
  voiceFile.value = null
  imageMeta.value = null
  voiceMeta.value = null
  imagePreview.value = ''
  cleanupDictationState()
  if (imageInput.value) imageInput.value.value = ''
  if (voiceInput.value) voiceInput.value.value = ''
}

async function handleSubmit() {
  const content = normalizedManualContent.value
  if (!content) {
    notify('先写一句，或者先让图片分析帮你提炼一下重点')
    return
  }
  if (!isBackgroundComplete.value) {
    notify(`背景补充未完成：${missingBackgroundFields.value.join('、')}`)
    return
  }
  submitting.value = true
  try {
    const payload = {
      content,
      mood_tags: selectedMoodTags.value,
      image_url: null,
      voice_url: null,
      mood_score: form.moodScore,
      interaction_freq: form.interactionFreq === null ? null : Number(form.interactionFreq),
      interaction_initiative: form.initiative || null,
      deep_conversation: form.deepConversation,
      task_completed: form.taskCompleted,
    }
    if (experienceMode.value.isDemoMode) {
      notify('样例记录已重置')
      resetForm()
      return
    }
    if (imageFile.value) payload.image_url = await uploadAttachment('image', imageFile.value)
    if (voiceFile.value) payload.voice_url = await uploadAttachment('voice', voiceFile.value)
    await checkinStore.submit(activePairId.value, payload)
    if (imageFile.value && imageAnalysis.value) {
      notify('已保存，回看时只展示分析结果')
    } else {
      notify('已保存')
    }
    resetForm()
  } catch (error) {
    notify(error.message || '这次没保存上，请稍后再试')
  } finally {
    submitting.value = false
  }
}

async function ensureAgentSession() {
  if (agentSessionId.value) return agentSessionId.value
  const session = await api.createAgentSession(userStore.currentPair?.id || null)
  agentSessionId.value = session.session_id || session.id
  const history = await api.getAgentMessages(agentSessionId.value).catch(() => [])
  if (Array.isArray(history) && history.length && !messages.value.length) {
    messages.value = history.filter((item) => item.role === 'user' || item.role === 'assistant')
  }
  return agentSessionId.value
}

async function sendChat() {
  const input = chatInput.value.trim()
  if (!input || agentSending.value) return
  agentSending.value = true
  messages.value.push({ role: 'user', content: input })
  chatInput.value = ''
  if (sessionStorage.getItem('qj_token') === 'demo-mode') {
    const reply = '听得出来你今天真的受累了~ 抱抱你！其实你不是在计较事情本身，只是特别希望对方能看到你默默抗下的辛苦，多给你一点心疼和体贴呀~'
    messages.value.push({ role: 'assistant', content: reply })
    lastAgentReply.value = reply
    agentSending.value = false
    return
  }
  try {
    const sessionId = await ensureAgentSession()
    const res = await api.chatWithAgent(sessionId, input)
    const reply = res.reply || res.content || '收到，我帮你整理一下。'
    messages.value.push({ role: 'assistant', content: reply })
    lastAgentReply.value = reply
    if (res.action === 'checkin_extracted') notify('已帮你整理好今天的记录')
  } catch (error) {
    messages.value.push({ role: 'assistant', content: error.message || '暂时无法回复，请稍后再试。' })
  } finally {
    agentSending.value = false
  }
}

function replayAgentReply() {
  if (!lastAgentReply.value) {
    notify('还没有回复')
    return
  }
  if (!('speechSynthesis' in window)) {
    notify('浏览器不支持朗读')
    return
  }
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(lastAgentReply.value)
  utterance.lang = 'zh-CN'
  window.speechSynthesis.speak(utterance)
}

async function toggleVoiceInput() {
  if (asrActive.value) {
    stopVoiceInput()
    return
  }
  if (asrFinalizing.value) {
    notify('正在整理最后一句')
    return
  }
  if (!experienceMode.value.canUseVoice) {
    notify(featureUnavailableReason('voice', experienceMode.value))
    return
  }
  try {
    voiceFallbackTried = false
    if (experienceMode.value.isDemoMode) {
      startBrowserVoice()
    } else {
      await ensureAgentSession()
      voiceController.value = createBackendRealtimeAsr({
        getSocketUrl: () => api.buildRealtimeAsrSocketUrl(),
        onActive: () => { asrActive.value = true; asrFinalizing.value = false },
        onStatus: (text) => { voiceStatus.value = text },
        onPartial: (text) => {
          if (!asrActive.value || asrFinalizing.value) return
          chatInput.value = text
          voiceStatus.value = '正在把语音转成文字。'
        },
        onFinal: handleVoiceFinal,
        onError: handleBackendVoiceError,
      })
      await voiceController.value.start()
    }
  } catch (error) {
    try {
      startBrowserVoice(error.message)
    } catch (fallbackError) {
      cleanupVoiceState()
      notify(fallbackError.message || error.message || '无法开启语音')
    }
  }
}

function handleBackendVoiceError(message) {
  cleanupVoiceState()
  if (!voiceFallbackTried && mode.value === 'voice') {
    voiceFallbackTried = true
    try {
      startBrowserVoice(message)
      return
    } catch {
      // Fall through to the backend message if browser speech is unavailable.
    }
  }
  notify(message)
}

function startBrowserVoice(reason = '') {
  voiceController.value = startBrowserSpeech({
    reason,
    onActive: () => { asrActive.value = true; asrFinalizing.value = false },
    onStatus: (text) => { voiceStatus.value = text },
    onPartial: (text) => {
      if (!asrActive.value || asrFinalizing.value) return
      chatInput.value = text
    },
    onFinal: handleVoiceFinal,
    onError: (message) => { cleanupVoiceState(); notify(message) },
  })
}

async function handleVoiceFinal(text) {
  const finalText = String(text || chatInput.value || '').trim()
  if (finalText) chatInput.value = finalText
  cleanupVoiceState('转写完成。')
  if (finalText) await sendChat()
}

function cleanupVoiceState(status = '') {
  asrActive.value = false
  asrFinalizing.value = false
  voiceStatus.value = status
  voiceController.value = null
}

function stopVoiceInput(options = {}) {
  if (!voiceController.value) {
    cleanupVoiceState()
    return
  }
  asrActive.value = false
  asrFinalizing.value = !options.discard
  voiceStatus.value = options.discard ? '' : '正在整理最后一句。'
  voiceController.value.stop?.({ discard: Boolean(options.discard) })
  if (options.discard) cleanupVoiceState()
}

onBeforeUnmount(() => {
  clearDictationLongPressTimer()
  voiceController.value?.cleanup?.()
  dictationController.value?.cleanup?.()
  cleanupVoiceState()
  cleanupDictationState()
  revokeImagePreview()
})

onMounted(() => {
  const incomingDraft = consumeChatDraftToCheckin()
  if (incomingDraft?.content) {
    mergeVoiceTextIntoContent(incomingDraft.content)
    notify('已把聊天里的内容带到今日记录里')
  }
})
</script>

<style scoped>
.checkin-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 28px;
}
.checkin-mode {
  width: min(420px, 100%);
  margin: 0 0 18px;
}
.checkin-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}
.record-editor,
.context-panel,
.attachment-panel,
.voice-draft {
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.72);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(37, 40, 33, 0.04);
}
.record-editor,
.voice-draft {
  padding: 24px;
  min-width: 0;
}
.record-editor__head,
.voice-draft__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.record-editor__head h3,
.voice-draft__head h3,
.attachment-panel h3 {
  font-family: var(--font-serif);
  font-size: 21px;
}
.checkin-pair-picker {
  align-self: start;
  justify-self: end;
  display: inline-grid;
  width: min(126px, 100%);
  min-width: 0;
  margin-left: auto;
}

.checkin-pair-picker select {
  min-height: 32px;
  width: 100%;
  padding: 5px 28px 5px 10px;
  border: 1px solid rgba(189, 75, 53, 0.18);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.78);
  color: var(--seal-deep);
  font: inherit;
  font-size: 12px;
  font-weight: 800;
}
.record-content-field {
  gap: 8px;
  min-width: 0;
}
.record-input-shell {
  display: grid;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  padding: 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.7);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.record-input-shell:focus-within,
.record-input-shell.is-listening,
.record-input-shell.has-dictation-draft {
  border-color: rgba(189, 75, 53, 0.3);
  background: rgba(255, 253, 250, 0.86);
  box-shadow: 0 0 0 3px rgba(215, 104, 72, 0.08);
}
.record-textarea {
  min-height: 240px;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  padding: 10px;
  border: 0;
  background: transparent;
  box-shadow: none;
  font-family: var(--font-serif);
  font-size: 18px;
  line-height: 1.85;
  overflow-x: hidden;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
  resize: vertical;
}
.record-textarea:focus {
  outline: none;
  box-shadow: none;
}
.dictation-dock {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
  min-height: 46px;
  padding: 8px 2px 0;
  border-top: 1px solid rgba(68, 52, 40, 0.08);
}
.dictation-status {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
  gap: 8px;
  color: var(--seal-deep);
  font-size: 13px;
  line-height: 1.45;
}
.dictation-status.muted {
  color: var(--ink-faint);
}
.dictation-status p {
  min-width: 0;
  max-height: 6.6em;
  margin: 0;
  overflow: hidden;
  overflow-y: auto;
  overflow-wrap: anywhere;
  text-overflow: ellipsis;
  white-space: normal;
  word-break: break-word;
}
.dictation-dot,
.dictation-pulse {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: rgba(189, 75, 53, 0.42);
}
.dictation-pulse {
  background: var(--danger);
  box-shadow: 0 0 0 0 rgba(189, 75, 53, 0.34);
  animation: dictationPulse 1.1s ease-out infinite;
}
.dictation-actions {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 6px;
}
.dictation-icon-button {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 1px solid rgba(189, 75, 53, 0.2);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.86);
  color: var(--seal-deep);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}
.dictation-icon-button:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.34);
  background: rgba(255, 246, 241, 0.96);
}
.dictation-icon-button:disabled {
  cursor: wait;
  opacity: 0.74;
  transform: none;
}
.dictation-icon-button--stop {
  border-color: rgba(189, 75, 53, 0.36);
  background: rgba(243, 216, 208, 0.52);
  color: var(--danger);
}
.dictation-icon-button--send {
  border-color: rgba(78, 116, 91, 0.34);
  background: rgba(235, 242, 232, 0.84);
  color: var(--moss-deep);
}
.dictation-icon-button--ghost {
  border-color: rgba(68, 52, 40, 0.12);
  color: var(--ink-soft);
}
.spin-icon {
  animation: spin 0.9s linear infinite;
}
@keyframes dictationPulse {
  0% { box-shadow: 0 0 0 0 rgba(189, 75, 53, 0.34); }
  100% { box-shadow: 0 0 0 9px rgba(189, 75, 53, 0); }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.voice-toolbar p {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.6;
}
.evidence-strip,
.upload-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.seal-tag,
.evidence-pill {
  padding: 5px 9px;
  border: 1px solid rgba(189, 75, 53, 0.22);
  border-radius: var(--radius-md);
  background: rgba(255, 253, 250, 0.68);
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 700;
}
.seal-tag--muted,
.evidence-pill {
  color: var(--ink-soft);
  border-color: var(--border);
}
.text-button {
  border: 0;
  background: transparent;
  color: var(--seal-deep);
  font-weight: 700;
  cursor: pointer;
}
.mood-field {
  margin: 18px 0;
}
.mood-field__head,
.mood-field__actions,
.mood-custom-field__row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mood-field__head {
  justify-content: space-between;
}
.mood-field__actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}
.mood-field__empty {
  color: var(--ink-faint);
  font-size: 12px;
}
.mood-presets {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.mood-presets > span {
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}
.mood-tag-item {
  position: relative;
  display: inline-flex;
}
.mood-tag-item__remove {
  position: absolute;
  top: -6px;
  right: -6px;
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border: 1px solid rgba(189, 75, 53, 0.22);
  border-radius: 999px;
  background: var(--paper-strong);
  color: var(--seal-deep);
  box-shadow: var(--shadow-xs);
}
.mood-custom-field {
  display: grid;
  gap: 7px;
  margin-top: 14px;
}
.mood-custom-field__input {
  flex: 1;
  min-width: 0;
  min-height: 34px;
  padding: 7px 11px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.68);
}
.mood-tags .tag {
  border-style: dashed;
}
.record-aside {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.record-support-grid {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.context-panel,
.attachment-panel {
  padding: 16px;
}

.attachment-panel {
  grid-column: 1 / -1;
}
.context-panel summary,
.attachment-panel summary {
  cursor: pointer;
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 700;
}

.context-panel .form-stack,
.attachment-panel .upload-row:first-of-type {
  margin-top: 14px;
}
.context-score-grid {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}
.context-panel .context-score-button {
  min-height: 40px;
  padding: 0;
  border-radius: 14px;
  font-size: 15px;
}
.context-panel .option-grid--two .select-card,
.context-panel .option-grid--three .select-card {
  min-height: 44px;
  padding: 8px;
}
.checkin-submit-bar {
  grid-column: 1 / -1;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.82);
  box-shadow: 0 10px 30px rgba(74, 55, 43, 0.08);
}
.upload-preview,
.voice-preview {
  margin-top: 12px;
}
.upload-preview img {
  max-width: 220px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
}
.voice-preview,
.voice-toolbar {
  padding: 10px;
  border: 1px dashed rgba(78, 116, 91, 0.3);
  border-radius: var(--radius-lg);
  background: rgba(235, 242, 232, 0.4);
}
.voice-preview {
  display: grid;
  gap: 4px;
  font-size: 13px;
}
.voice-preview span {
  max-height: 7.2em;
  overflow-y: auto;
  overflow-wrap: anywhere;
}
.image-insight-card {
  display: grid;
  gap: 7px;
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(189, 75, 53, 0.18);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.62);
}
.image-insight-card span {
  color: var(--seal);
  font-size: 12px;
  font-weight: 800;
}
.image-insight-card strong {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 16px;
}
.image-insight-card p {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.6;
}
.image-emotion-card {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgba(78, 116, 91, 0.18);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg, rgba(235, 242, 232, 0.82), rgba(255, 253, 250, 0.86));
}
.image-emotion-card > span {
  color: var(--moss-deep);
  letter-spacing: 0.08em;
}
.image-emotion-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.image-emotion-card__tags strong {
  padding: 7px 11px;
  border: 1px solid rgba(189, 75, 53, 0.2);
  border-radius: 999px;
  background: rgba(255, 246, 241, 0.92);
  color: var(--seal-deep);
  font-size: 15px;
}
.voice-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.voice-toolbar strong {
  font-family: var(--font-serif);
  font-size: 17px;
}
.chat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 360px;
  overflow-y: auto;
  padding: 4px 0 18px;
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
  border: 1px solid rgba(78, 116, 91, 0.25);
  border-radius: var(--radius-lg);
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
  max-width: 75%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.7);
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.chat-msg--user .chat-msg__bubble {
  border-color: rgba(189, 75, 53, 0.24);
  background: rgba(243, 216, 208, 0.42);
}
.voice-input {
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.voice-chat-textarea {
  min-height: 220px;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
}
@media (max-width: 900px) {
  .checkin-workbench {
    grid-template-columns: 1fr;
  }
  .record-support-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 600px) {
  .checkin-page {
    width: min(100% - 20px, var(--content-max));
  }
  .record-editor,
  .voice-draft {
    padding: 16px;
  }
  .record-editor__head,
  .voice-draft__head {
    flex-wrap: wrap;
  }
  .checkin-pair-picker {
    width: min(126px, 46vw);
  }
  .record-support-grid {
    grid-template-columns: 1fr;
  }
  .context-score-grid {
    gap: 5px;
  }
  .context-panel .context-score-button {
    min-height: 36px;
    border-radius: 12px;
  }
  .record-textarea {
    min-height: 160px;
    font-size: 16px;
  }
  .voice-chat-textarea {
    min-height: 210px;
  }
  .dictation-dock {
    align-items: flex-start;
    flex-direction: column;
  }
  .dictation-status,
  .dictation-actions {
    width: 100%;
  }
  .dictation-status p {
    white-space: normal;
  }
  .dictation-actions {
    justify-content: flex-end;
  }
  .voice-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .chat-msg__bubble {
    max-width: calc(100% - 48px);
  }
}
</style>

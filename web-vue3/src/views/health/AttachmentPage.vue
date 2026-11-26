<template>
  <div class="attach-page page-shell page-shell--narrow page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">依恋</p>
        <h2>{{ pageTitle }}</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>
    <div class="card card-accent">
      <div class="card-header">
        <div>
          <p class="eyebrow">分析</p>
          <h3>{{ panelTitle }}</h3>
        </div>
        <button class="btn btn-primary btn-sm" :disabled="analyzing" @click="runAnalysis">
          {{ actionLabel }}
        </button>
      </div>
      <div
        v-if="normalizedResult"
        class="attach-result"
        :class="{ 'attach-result--solo': !showPartnerAttachment }"
      >
        <div class="attach-item">
          <span>{{ myAttachmentLabel }}</span>
          <strong>{{ normalizedResult.my.label }}</strong>
          <p>{{ attachmentItemSummary(normalizedResult.my) }}</p>
        </div>
        <div v-if="showPartnerAttachment" class="attach-item">
          <span>{{ partnerAttachmentLabel }}</span>
          <strong>{{ normalizedResult.partner.label }}</strong>
          <p>{{ attachmentItemSummary(normalizedResult.partner) }}</p>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>{{ emptyStateText }}</p>
        <p class="attach-guide">
          依恋倾向不是固定问卷答题，而是结合平时留下的日常记录与互动方式自动整理，帮助你看见彼此在亲密、沟通和回应节奏上的习惯。
        </p>
        <p v-if="sampleProgressText" class="attach-progress">{{ sampleProgressText }}</p>
        <div class="hero-actions attach-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="$router.push('/checkin')">去写今日记录</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/health-test')">先做关系体检</button>
        </div>
      </div>
      <p v-if="analysisNotice" class="attach-notice" role="status">{{ analysisNotice }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { resolveRelationshipDisplayPair } from '@/utils/relationshipDisplay'
import { createRefreshAttemptGuard, parseRetryAfterSeconds } from '@/utils/refreshGuards'

const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const analyzing = ref(false)
const result = ref(null)
const analysisNotice = ref('')
const sampleCounts = ref(null)
let requestVersion = 0
let disposed = false
const analysisScope = computed(() => `${userStore.token || ''}::${userStore.me?.id || ''}::${userStore.activePairId || 'solo'}`)
const attachmentAnalysisGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })

const LABELS = {
  secure: '安全型',
  anxious: '焦虑型',
  avoidant: '回避型',
  fearful: '恐惧型',
  unknown: '未分析',
}

const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    testingUnrestricted: userStore.testingUnrestricted,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const relationshipDisplayPair = computed(() => resolveRelationshipDisplayPair({
  activePair: userStore.activePair,
  currentPair: userStore.currentPair,
}))

const demoAttachmentResult = computed(() => {
  const base = cloneDemo(demoFixture.attachmentAnalysis || {})
  if (experienceMode.value.isPairExperience) return base
  return {
    scope: 'solo',
    analyzed_at: base.analyzed_at,
    my_attachment: base.my_attachment,
    partner_attachment: null,
  }
})

const pageTitle = computed(() =>
  experienceMode.value.isPairExperience ? '依恋倾向分析' : '我的依恋倾向'
)

const panelTitle = computed(() =>
  experienceMode.value.isPairExperience ? '双方依恋倾向' : '我的依恋倾向'
)

const actionLabel = computed(() => {
  if (analyzing.value) return '正在整理...'
  if (experienceMode.value.isDemoMode) return normalizedResult.value ? '刷新样例' : '查看样例'
  return normalizedResult.value ? '重新整理' : '开始整理'
})

const myAttachmentLabel = computed(() =>
  experienceMode.value.isPairExperience ? '我的倾向' : '我的倾向'
)

const partnerAttachmentLabel = computed(() =>
  userStore.partnerName ? `${userStore.partnerName}的倾向` : '对方倾向'
)

const normalizedResult = computed(() => normalizeAttachmentResult(result.value))
const showPartnerAttachment = computed(() =>
  Boolean(experienceMode.value.isPairExperience && normalizedResult.value?.partner)
)

const emptyStateText = computed(() => {
  if (experienceMode.value.isDemoMode) {
    return '点“查看样例”。'
  }
  if (experienceMode.value.canBypassFeatureGates) {
    return '测试账号可直接整理。'
  }
  if (experienceMode.value.isPairExperience) {
    return '双方各留下 5 条对伴侣可见的记录后可分析。'
  }
  return '完成 5 条记录后可分析。'
})

const sampleProgressText = computed(() => {
  if (experienceMode.value.isDemoMode || !experienceMode.value.isPairExperience) return ''
  const counts = sampleCounts.value
  if (!counts || !Number(counts.required)) return ''
  return `当前你已共享 ${counts.my ?? 0}/${counts.required} 条，对方已共享 ${counts.partner ?? 0}/${counts.required} 条。`
})

function attachmentItemSummary(item) {
  if (!item || item.type === 'unknown') {
    const required = Number(sampleCounts.value?.required || 5)
    return experienceMode.value.isPairExperience
      ? `共享记录还不足 ${required} 条，暂时无法判断。`
      : `个人记录还不足 ${required} 条，暂时无法判断。`
  }
  return item.analysis || '这次结果先作参考。'
}

watch(analysisScope, () => {
  const version = ++requestVersion
  result.value = null
  analysisNotice.value = ''
  sampleCounts.value = null
  analyzing.value = false
  if (userStore.isDemoMode || userStore.me?.id) void loadExistingAnalysis(version)
}, { immediate: true, flush: 'sync' })

onBeforeUnmount(() => { disposed = true; requestVersion++ })

function normalizeAttachmentItem(item) {
  if (!item) return null
  if (typeof item === 'string') {
    return {
      type: item,
      label: LABELS[item] || item || LABELS.unknown,
      confidence: null,
      analysis: '',
      growth_suggestion: '',
    }
  }

  const type = String(item.type || item.style || 'unknown').trim() || 'unknown'
  const confidence = Number(item.confidence)
  return {
    type,
    label: item.label || LABELS[type] || LABELS.unknown,
    confidence: Number.isFinite(confidence) ? confidence : null,
    analysis: String(item.analysis || '').trim(),
    growth_suggestion: String(item.growth_suggestion || '').trim(),
  }
}

function normalizeAttachmentResult(payload) {
  if (!payload) return null

  if (payload.my_attachment || payload.partner_attachment) {
    const my = normalizeAttachmentItem(payload.my_attachment)
    const partner = normalizeAttachmentItem(payload.partner_attachment)
    return my ? { my, partner } : null
  }

  if (payload.my_style || payload.partner_style) {
    const my = normalizeAttachmentItem(payload.my_style)
    const partner = normalizeAttachmentItem(payload.partner_style)
    return my ? { my, partner } : null
  }

  if (payload.attachment_a || payload.attachment_b) {
    const isUserA = String(userStore.me?.id || '') === String(relationshipDisplayPair.value?.user_a_id || '')
    const my = normalizeAttachmentItem(isUserA ? payload.attachment_a : payload.attachment_b)
    const partner = normalizeAttachmentItem(isUserA ? payload.attachment_b : payload.attachment_a)
    return my ? { my, partner } : null
  }

  return null
}

function hasMeaningfulResult(payload) {
  const normalized = normalizeAttachmentResult(payload)
  if (!normalized?.my) return false
  const hasMy = Boolean(normalized.my.type && normalized.my.type !== 'unknown')
  const hasPartner = Boolean(normalized.partner?.type && normalized.partner.type !== 'unknown')
  return hasMy || hasPartner
}

async function loadExistingAnalysis(version) {
  if (experienceMode.value.isDemoMode) {
    result.value = demoAttachmentResult.value
    analysisNotice.value = ''
    return
  }

  try {
    const response = await api.getAttachmentAnalysis(experienceMode.value.activePairId || null)
    if (disposed || version !== requestVersion) return
    sampleCounts.value = response?.sample_counts || null
    result.value = hasMeaningfulResult(response) ? response : null
  } catch {
    if (!disposed && version === requestVersion) result.value = null
  }
}

async function runAnalysis() {
  if (!experienceMode.value.isDemoMode) {
    const remainingSeconds = attachmentAnalysisGuard.getRemainingSeconds()
    if (remainingSeconds > 0) {
      showToast(`依恋分析得有点频繁了，请 ${remainingSeconds} 秒后再试`)
      return
    }
    attachmentAnalysisGuard.markRun()
  }
  analyzing.value = true
  const version = ++requestVersion
  try {
    if (experienceMode.value.isDemoMode) {
      result.value = demoAttachmentResult.value
      analysisNotice.value = ''
      showToast('样例分析')
      return
    }

    const response = await api.triggerAttachmentAnalysis(experienceMode.value.activePairId || null)
    if (disposed || version !== requestVersion) return
    sampleCounts.value = response?.sample_counts || sampleCounts.value
    const meaningful = hasMeaningfulResult(response)
    const status = String(response?.analysis_status || '').trim()

    if (!meaningful || status === 'insufficient_data') {
      result.value = null
      analysisNotice.value = response?.reason
        || response?.message
        || '双方共享记录还不足以判断依恋倾向，多补充几条对伴侣可见的记录后再试。'
      showToast(response?.message || '当前记录还不足以判断依恋倾向')
      return
    }

    result.value = response
    if (status === 'partial') {
      analysisNotice.value = response?.reason || response?.message || ''
      showToast(response?.message || '已完成一方依恋倾向整理，另一方记录还不够')
      return
    }

    analysisNotice.value = ''
    showToast(
      experienceMode.value.isPairExperience
        ? '双方依恋倾向已整理好'
        : '你的依恋倾向已整理好'
    )
  } catch (error) {
    if (disposed || version !== requestVersion) return
    if (error?.statusCode === 429) {
      attachmentAnalysisGuard.setCooldown(parseRetryAfterSeconds(error.message))
    }
    if (error?.statusCode === 400 && error?.message) {
      analysisNotice.value = error.message
    }
    showToast(error.message || '依恋倾向没整理出来，请稍后再试')
  } finally {
    if (!disposed && version === requestVersion) analyzing.value = false
  }
}
</script>

<style scoped>
.attach-result {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.attach-result--solo {
  grid-template-columns: 1fr;
}

.attach-item {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--warm-50);
  text-align: center;
}

.attach-item span {
  display: block;
  font-size: 12px;
  color: var(--ink-faint);
  margin-bottom: 6px;
}

.attach-item strong {
  display: block;
  font-size: 18px;
  color: var(--warm-600);
  font-family: var(--font-serif);
}

.attach-item p {
  margin: 10px 0 0;
  color: var(--ink-soft);
  line-height: 1.65;
}

.attach-progress {
  margin: 8px 0 0;
  color: var(--ink-faint);
  font-size: 13px;
}

.attach-guide {
  margin: 8px auto 0;
  max-width: 520px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.68;
}

.attach-actions {
  margin-top: 14px;
  justify-content: center;
}

.attach-notice {
  margin: 14px 0 0;
  padding: 12px 14px;
  border: 1px solid rgba(189, 75, 53, 0.22);
  border-radius: var(--radius-md);
  background: rgba(255, 246, 240, 0.9);
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 640px) {
  .attach-result {
    grid-template-columns: 1fr;
  }
}
</style>

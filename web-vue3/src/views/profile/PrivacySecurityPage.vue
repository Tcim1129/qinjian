<template>
  <div class="privacy-page page-shell page-shell--narrow page-stack">
    <div class="page-head">
      <p class="eyebrow">隐私与安全</p>
      <h2>账号和记录设置</h2>
    </div>

    <section class="privacy-panel">
      <div class="card-header privacy-panel__head">
        <div>
          <p class="eyebrow">媒体与结果</p>
          <h3>图片和音频按私有上传处理</h3>
        </div>
        <button class="btn btn-primary btn-sm" type="button" :disabled="saving" @click="savePrivacyPrefs">
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>

      <div class="privacy-summary">
        <article class="privacy-summary__card">
          <strong>原始媒体</strong>
          <span>后台短期保留，不提供下载。</span>
        </article>
        <article class="privacy-summary__card">
          <strong>分析结果</strong>
          <span>转写、图像分析和回看摘要会保存。</span>
        </article>
      </div>

      <label class="security-toggle">
        <span>
          <strong>辅助整理</strong>
          <span class="security-toggle__text">关闭后只保存记录。</span>
        </span>
        <input v-model="assistEnabled" type="checkbox" />
      </label>
    </section>

    <section class="privacy-panel">
      <div class="card-header">
        <div>
          <p class="eyebrow">保护状态</p>
          <h3>当前账号安全概览</h3>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="loading" @click="handleLoadPrivacyCenter">
          {{ loading ? '查看中...' : '刷新' }}
        </button>
      </div>

      <div class="status-grid">
        <div v-for="item in statusItems" :key="item.label" class="status-item">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>

    <section id="account-deletion" class="privacy-panel privacy-panel--deletion">
      <div class="card-header">
        <div>
          <p class="eyebrow">账号注销</p>
          <h3>注销申请与冷静期管理</h3>
        </div>
        <span class="deletion-badge" :class="`deletion-badge--${deletionStateTone}`">
          {{ deletionStateLabel }}
        </span>
      </div>

      <p class="deletion-desc">
        发起注销后将进入 {{ deleteGraceDays }} 天冷静期，期间可随时撤回；冷静期满后，系统会按隐私保护规则清理账号及关联个人数据。
      </p>

      <div v-if="latestDeleteRequest" class="deletion-meta">
        <div>
          <span>申请时间</span>
          <strong>{{ formatDateTime(latestDeleteRequest.requested_at) }}</strong>
        </div>
        <div v-if="latestDeleteRequest.status === 'pending' && latestDeleteRequest.scheduled_for">
          <span>预计执行时间</span>
          <strong>{{ formatDateTime(latestDeleteRequest.scheduled_for) }}</strong>
        </div>
        <div v-else-if="latestDeleteRequest.cancelled_at">
          <span>撤回时间</span>
          <strong>{{ formatDateTime(latestDeleteRequest.cancelled_at) }}</strong>
        </div>
        <div v-if="latestDeleteRequest.review_note">
          <span>处理说明</span>
          <strong>{{ latestDeleteRequest.review_note }}</strong>
        </div>
      </div>

      <p v-if="userStore.isDemoMode" class="deletion-demo-note">
        体验样例模式仅展示入口，登录真实账号后可在此提交或撤回账号注销申请。
      </p>

      <div v-else-if="canCancelDeletion" class="deletion-actions">
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          :disabled="deletionBusy"
          @click="handleCancelDeletion"
        >
          {{ deletionBusy ? '处理中...' : '撤回注销申请' }}
        </button>
      </div>

      <div v-else-if="latestDeleteRequest?.status === 'manual_review'" class="deletion-actions">
        <span class="deletion-demo-note">注销申请正在人工复核中，请留意后续通知。</span>
      </div>

      <div v-else class="deletion-request-box">
        <div v-if="!confirmDeleteOpen" class="deletion-actions">
          <button
            class="btn btn-danger-outline btn-sm"
            type="button"
            :disabled="deletionBusy"
            @click="confirmDeleteOpen = true"
          >
            申请注销账号
          </button>
        </div>
        <div v-else class="deletion-confirm">
          <label class="deletion-confirm__check">
            <input v-model="confirmDeleteChecked" type="checkbox" />
            <span>我已知晓注销申请提交后将进入 {{ deleteGraceDays }} 天冷静期，冷静期满后账号及个人数据将被清理且不可恢复。</span>
          </label>
          <div class="deletion-actions">
            <button
              class="btn btn-danger btn-sm"
              type="button"
              :disabled="!confirmDeleteChecked || deletionBusy"
              @click="handleRequestDeletion"
            >
              {{ deletionBusy ? '提交中...' : '确认提交注销申请' }}
            </button>
            <button
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="deletionBusy"
              @click="closeDeleteConfirm"
            >
              先不注销
            </button>
          </div>
        </div>
      </div>
    </section>

    <section class="privacy-panel">
      <div class="card-header">
        <div>
          <p class="eyebrow">安全记录</p>
          <h3>最近的隐私相关操作</h3>
        </div>
      </div>

      <div v-if="auditEntries.length" class="audit-list">
        <article v-for="entry in auditEntries" :key="entry.event_id">
          <strong>{{ entry.event_label }}</strong>
          <p>{{ entry.summary || '已记录一次隐私相关操作。' }}</p>
          <span class="audit-list__date">{{ formatDateTime(entry.occurred_at) }}</span>
        </article>
      </div>
      <p v-else class="empty-state">最近还没有新的安全记录。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'
import { formatBeijingDateTime } from '@/utils/datetime'

const userStore = useUserStore()
const showToast = inject('showToast', null)

const loading = ref(false)
const saving = ref(false)
const deletionBusy = ref(false)
const confirmDeleteOpen = ref(false)
const confirmDeleteChecked = ref(false)
const privacyStatus = ref(null)
const auditEntries = ref([])
const assistEnabled = ref(true)
const privacyRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 3, windowMs: 60 * 1000 })

watch(
  () => userStore.me,
  (profile) => {
    assistEnabled.value = profile?.ai_assist_enabled !== false
  },
  { immediate: true }
)

const deleteGraceDays = computed(() => {
  const days = Number(privacyStatus.value?.delete_grace_days)
  return Number.isFinite(days) && days > 0 ? days : 7
})

const latestDeleteRequest = computed(() => privacyStatus.value?.latest_delete_request || null)
const canCancelDeletion = computed(() => Boolean(
  latestDeleteRequest.value?.can_cancel
    || latestDeleteRequest.value?.status === 'pending'
))

const deletionStateLabel = computed(() => {
  const status = String(latestDeleteRequest.value?.status || '').trim()
  if (status === 'pending') return '冷静期中'
  if (status === 'manual_review') return '人工复核中'
  if (status === 'cancelled') return '已撤回'
  if (status === 'executed') return '已执行'
  if (status === 'rejected') return '未通过'
  return '未发起'
})

const deletionStateTone = computed(() => {
  const status = String(latestDeleteRequest.value?.status || '').trim()
  if (status === 'pending' || status === 'manual_review') return 'warn'
  if (status === 'executed') return 'danger'
  return 'muted'
})

const statusItems = computed(() => {
  const status = privacyStatus.value || {}
  return [
    { label: '媒体上传', value: '图片/音频私有上传' },
    { label: '结果保存', value: '分析结果长期保留' },
    { label: '原件下载', value: '不提供' },
    { label: '辅助整理', value: assistEnabled.value ? '已开启' : '已关闭' },
    { label: '上传文件访问', value: status.private_upload_access === false ? '公开访问' : '需授权访问' },
    { label: '安全审计', value: status.audit_enabled === false ? '未开启' : '已开启' },
  ]
})

onMounted(() => {
  loadPrivacyCenter()
})

function formatDateTime(value) {
  return formatBeijingDateTime(value)
}

function closeDeleteConfirm() {
  confirmDeleteOpen.value = false
  confirmDeleteChecked.value = false
}

async function handleRequestDeletion() {
  if (userStore.isDemoMode || !confirmDeleteChecked.value || deletionBusy.value) return
  deletionBusy.value = true
  try {
    const req = await api.requestPrivacyDelete()
    if (privacyStatus.value) {
      privacyStatus.value = { ...privacyStatus.value, latest_delete_request: req }
    }
    closeDeleteConfirm()
    await loadPrivacyCenter()
    showToast?.('已提交注销申请，进入冷静期后仍可随时撤回')
  } catch (e) {
    showToast?.(e.message || '注销申请没提交成功，请稍后再试')
  } finally {
    deletionBusy.value = false
  }
}

async function handleCancelDeletion() {
  if (userStore.isDemoMode || deletionBusy.value) return
  deletionBusy.value = true
  try {
    const req = await api.cancelPrivacyDelete()
    if (privacyStatus.value) {
      privacyStatus.value = { ...privacyStatus.value, latest_delete_request: req }
    }
    await loadPrivacyCenter()
    showToast?.('已撤回账号注销申请')
  } catch (e) {
    showToast?.(e.message || '撤回没成功，请稍后再试')
  } finally {
    deletionBusy.value = false
  }
}

async function loadPrivacyCenter() {
  if (userStore.isDemoMode) {
    privacyStatus.value = {
      privacy_mode: 'cloud',
      private_upload_access: true,
      audit_enabled: true,
      latest_delete_request: null,
    }
    auditEntries.value = [
      {
        event_id: 'demo-privacy-1',
        event_label: '查看隐私与安全',
        summary: '样例账号没有新增隐私记录。',
        occurred_at: new Date().toISOString(),
      },
    ]
    return
  }

  loading.value = true
  try {
    const [status, audit] = await Promise.all([
      api.getPrivacyStatus(),
      api.getPrivacyAudit(8),
    ])
    privacyStatus.value = status
    auditEntries.value = Array.isArray(audit) ? audit : []
  } catch (e) {
    showToast?.(e.message || '隐私设置没加载出来，请稍后再试')
  } finally {
    loading.value = false
  }
}

function handleLoadPrivacyCenter() {
  const remainingSeconds = privacyRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast?.(`安全状态刷新得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  privacyRefreshGuard.markRun()
  return loadPrivacyCenter()
}

async function savePrivacyPrefs() {
  saving.value = true
  try {
    const prefs = {
      ai_assist_enabled: assistEnabled.value,
    }
    if (userStore.isDemoMode) {
      userStore.me = {
        ...(userStore.me || {}),
        ...prefs,
      }
    } else {
      await userStore.updateMe(prefs)
      await loadPrivacyCenter()
    }
    showToast?.('隐私设置已保存')
  } catch (e) {
    showToast?.(e.message || '设置没保存上，请稍后再试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.privacy-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.82);
  box-shadow: 0 14px 28px rgba(91, 67, 51, 0.05);
}

.privacy-panel__head {
  align-items: center;
}

.privacy-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.privacy-summary__card {
  display: grid;
  gap: 10px;
  min-height: 132px;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 252, 248, 0.88), rgba(255, 250, 245, 0.72));
}

.privacy-summary__card strong {
  color: var(--ink);
  font-weight: 800;
  font-size: 17px;
}

.privacy-summary__card > span,
.security-toggle__text {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.75;
}

.security-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(241, 247, 239, 0.72);
}

.security-toggle > span {
  display: grid;
  gap: 4px;
}

.security-toggle strong {
  color: var(--ink);
}

.security-toggle input {
  accent-color: var(--seal);
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-item {
  min-height: 78px;
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(255, 251, 247, 0.68);
}

.status-item span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}

.status-item strong {
  color: var(--ink);
  font-size: 15px;
}

.audit-list {
  display: grid;
  gap: 10px;
}

.audit-list article {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(255, 251, 247, 0.68);
}

.audit-list strong {
  color: var(--ink);
}

.audit-list p {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.65;
}

.audit-list__date {
  color: var(--ink-faint);
  font-size: 12px;
}

.privacy-panel--deletion {
  border-color: rgba(189, 75, 53, 0.28);
}

.deletion-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.deletion-badge--muted {
  background: rgba(68, 52, 40, 0.08);
  color: var(--ink-soft);
}

.deletion-badge--warn {
  background: rgba(215, 104, 72, 0.14);
  color: var(--seal-deep);
}

.deletion-badge--danger {
  background: rgba(189, 75, 53, 0.18);
  color: var(--danger, #b53a2a);
}

.deletion-desc,
.deletion-demo-note {
  margin: 0;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.deletion-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.deletion-meta > div {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(255, 251, 247, 0.72);
}

.deletion-meta span {
  color: var(--ink-faint);
  font-size: 12px;
}

.deletion-meta strong {
  color: var(--ink);
  font-size: 14px;
}

.deletion-confirm {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(189, 75, 53, 0.24);
  border-radius: var(--radius-md);
  background: rgba(255, 246, 241, 0.85);
}

.deletion-confirm__check {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.65;
  cursor: pointer;
}

.deletion-confirm__check input {
  margin-top: 3px;
  accent-color: var(--seal-deep);
  flex-shrink: 0;
}

.deletion-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.btn-danger-outline {
  border: 1px solid rgba(189, 75, 53, 0.45);
  background: transparent;
  color: var(--danger, #b53a2a);
}

.btn-danger-outline:hover:not(:disabled) {
  background: rgba(189, 75, 53, 0.08);
}

.btn-danger {
  border: 1px solid var(--danger, #b53a2a);
  background: var(--danger, #b53a2a);
  color: #fff;
}

.btn-danger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .privacy-page {
    width: min(100% - 20px, var(--content-readable));
  }

  .privacy-summary,
  .status-grid,
  .deletion-meta {
    grid-template-columns: 1fr;
  }
}
</style>

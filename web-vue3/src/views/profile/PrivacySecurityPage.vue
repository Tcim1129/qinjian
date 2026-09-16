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
          <span class="audit-list__date">{{ formatDate(entry.occurred_at) }}</span>
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

const userStore = useUserStore()
const showToast = inject('showToast', null)

const loading = ref(false)
const saving = ref(false)
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

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
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

@media (max-width: 640px) {
  .privacy-page {
    width: min(100% - 20px, var(--content-readable));
  }

  .privacy-summary,
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>

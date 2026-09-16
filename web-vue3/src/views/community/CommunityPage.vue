<template>
  <div class="community-page page-shell page-shell--wide page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">技巧</p>
        <h2>不知道怎么开口时，先找一句</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>
    <div class="card">
      <div class="card-header">
        <div><p class="eyebrow">建议</p><h3>明天可以这样安排</h3></div>
        <div class="page-head__aside">
          <button class="btn btn-ghost btn-sm" :disabled="refreshingTips" @click="handleRefreshTips">
            {{ refreshingTips ? '刷新中...' : '刷新' }}
          </button>
          <button class="btn btn-secondary btn-sm" :disabled="generatingTip" @click="handleGenerateTip">
            {{ generatingTip ? '换一句中...' : '换一句' }}
          </button>
        </div>
      </div>
      <div v-if="tips.length" class="stack-list">
        <div v-for="tip in tips" :key="tip.id" class="stack-item">
          <div class="stack-item__icon stack-item__icon--gold">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 2 1.9 5.8L20 10l-6.1 2.2L12 18l-1.9-5.8L4 10l6.1-2.2z" stroke-linejoin="round"/></svg>
          </div>
          <div class="stack-item__content">
            <strong>{{ tip.title || tip.content }}</strong>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">还没有可参考的安排。</div>
    </div>

    <div class="card">
      <div class="card-header">
        <div><p class="eyebrow">提醒</p><h3>消息</h3></div>
        <button class="btn btn-ghost btn-sm" :disabled="refreshingNotifications" @click="handleLoadNotifications">
          {{ refreshingNotifications ? '刷新中...' : '刷新' }}
        </button>
      </div>
      <div v-if="notifications.length" class="stack-list">
        <button
          v-for="item in notifications"
          :key="item.id || item.created_at"
          class="stack-item community-notification"
          :class="{ 'is-link': item.target_path }"
          type="button"
          @click="openNotification(item)"
        >
          <div class="stack-item__icon stack-item__icon--warm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 15V11a6 6 0 1 0-12 0v4l-2 2h16z"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>
          </div>
          <div class="stack-item__content">
            <strong>{{ item.content }}</strong>
            <div class="stack-item__meta">{{ formatDate(item.created_at) }}</div>
          </div>
          <span v-if="!item.is_read" class="pill pill-warning">未读</span>
        </button>
      </div>
      <div v-else class="empty-state">暂时没有消息。</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'

const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast')
const tips = ref([])
const notifications = ref([])
const refreshingTips = ref(false)
const generatingTip = ref(false)
const refreshingNotifications = ref(false)
const tipsRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 3, windowMs: 60 * 1000 })
const tipGenerateGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })
const notificationsRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 3, windowMs: 60 * 1000 })
const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)
const relationshipDisplayPair = computed(() => userStore.activePair || null)
const resolvedTipScope = computed(() => relationshipDisplayPair.value?.type || 'solo')
const resolvedTipPairId = computed(() => relationshipDisplayPair.value?.id || null)
onMounted(() => {
  loadTips()
  loadNotifications()
})

async function loadTips({ announce = false } = {}) {
  if (experienceMode.value.isDemoMode) {
    tips.value = cloneDemo(demoFixture.communityTips)
    if (announce) showToast('已刷新样例建议')
    return
  }
  refreshingTips.value = true
  try {
    const res = await api.getCommunityTips(resolvedTipScope.value, resolvedTipPairId.value)
    const rawTips = Array.isArray(res) ? res : res.tips || []
    tips.value = rawTips
    if (announce) showToast('已按最新状态刷新')
  } catch {
    tips.value = []
    if (announce) showToast('这次没刷新出来，请稍后再试')
  } finally {
    refreshingTips.value = false
  }
}

async function generateTip() {
  generatingTip.value = true
  if (experienceMode.value.isDemoMode) {
    tips.value = [
      {
        id: `tip-demo-${Date.now()}`,
        title: '先补一句近况',
        content: '如果最近联系淡了，明天先发一句真实近况。',
      },
      ...tips.value,
    ]
    showToast('已换一条样例建议')
    generatingTip.value = false
    return
  }
  try {
    const res = await api.generateTip(resolvedTipScope.value, resolvedTipPairId.value)
    const nextTip = res?.tip
    if (nextTip) {
      tips.value = [
        nextTip,
        ...tips.value.filter((item, index) => index !== 0),
      ]
    }
    showToast('已更新一条明天建议')
  } catch (e) {
    showToast(e.message || '这次没换出来，请稍后再试')
  } finally {
    generatingTip.value = false
  }
}

function refreshTips() {
  return loadTips({ announce: true })
}

async function loadNotifications() {
  refreshingNotifications.value = true
  try {
    await userStore.loadNotifications()
    notifications.value = userStore.notifications
    return notifications.value
  } finally {
    refreshingNotifications.value = false
  }
}

function handleRefreshTips() {
  const remainingSeconds = tipsRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`建议刷新得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  tipsRefreshGuard.markRun()
  return refreshTips()
}

function handleGenerateTip() {
  const remainingSeconds = tipGenerateGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`换一句得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  tipGenerateGuard.markRun()
  return generateTip()
}

function handleLoadNotifications() {
  const remainingSeconds = notificationsRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`消息刷新得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  notificationsRefreshGuard.markRun()
  return loadNotifications()
}

function formatDate(v) {
  if (!v) return ''
  const d = new Date(v)
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function openNotification(item) {
  const targetPath = String(item?.target_path || '').trim()
  if (targetPath) {
    router.push(targetPath)
  }
}
</script>

<style scoped>
.community-notification {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
}

.community-notification.is-link {
  cursor: pointer;
}

.community-lead {
  margin-top: 10px;
  color: var(--ink-soft);
  line-height: 1.72;
}
</style>

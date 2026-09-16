<template>
  <div class="ld-page page-shell page-shell--narrow page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">{{ pageEyebrow }}</p>
        <h2>{{ pageTitle }}</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>
    <div class="card card-accent">
      <div class="card-header"><div><p class="eyebrow">{{ scoreEyebrow }}</p><h3>{{ scoreTitle }}</h3></div></div>
      <div v-if="health.health_index !== undefined" class="ld-score">
        <span class="ld-score__num">{{ health.health_index }}</span>
        <span class="ld-score__label">/ 100</span>
        <p v-if="health.summary" class="ld-score__summary">{{ health.summary }}</p>
      </div>
      <div v-else class="empty-state">正在加载...</div>
    </div>
    <div class="card">
      <div class="card-header"><div><p class="eyebrow">快捷</p><h3>{{ actionTitle }}</h3></div></div>
      <div class="option-grid option-grid--compact">
        <button v-for="(label, type) in LONG_DISTANCE_ACTIVITY_LABELS" :key="type" class="select-card" @click="createActivity(type)" type="button">{{ label }}</button>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><div><p class="eyebrow">活动</p><h3>{{ listTitle }}</h3></div></div>
      <div v-if="activities.length" class="stack-list">
        <div v-for="a in activities" :key="a.id" class="stack-item">
          <div class="stack-item__icon stack-item__icon--sage">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 2 1.9 5.8L20 10l-6.1 2.2L12 18l-1.9-5.8L4 10l6.1-2.2z" stroke-linejoin="round"/></svg>
          </div>
          <div class="stack-item__content">
            <strong>{{ a.title || longDistanceActivityLabel(a.activity_type || a.type) }}</strong>
            <div class="stack-item__meta">{{ activityStatusLabel(a) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">{{ emptyState }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { LONG_DISTANCE_ACTIVITY_LABELS, longDistanceActivityLabel } from '@/utils/displayText'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { createSoloConnectionActivityEntry, loadSoloConnectionWorkspace } from '@/utils/soloWorkspace'

const userStore = useUserStore()
const showToast = inject('showToast')
const health = ref({})
const activities = ref([])

const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)

const pageEyebrow = computed(() => (experienceMode.value.hasPairContext ? '异地' : '联系节奏'))
const pageTitle = computed(() => (experienceMode.value.hasPairContext ? '异地关系' : '先准备下一次联系'))
const scoreEyebrow = computed(() => (experienceMode.value.hasPairContext ? '健康指数' : '准备度'))
const scoreTitle = computed(() => (experienceMode.value.hasPairContext ? '关系健康度' : '联系准备度'))
const actionTitle = computed(() => (experienceMode.value.hasPairContext ? '安排一次同步' : '留一个联系计划'))
const listTitle = computed(() => (experienceMode.value.hasPairContext ? '近期的异地互动' : '近期的联系安排'))
const emptyState = computed(() => (experienceMode.value.hasPairContext ? '还没有异地互动记录。' : '还没有留下联系安排。'))

onMounted(() => loadData())

async function loadData() {
  if (experienceMode.value.isDemoMode) {
    health.value = cloneDemo(demoFixture.longDistance.health)
    activities.value = cloneDemo(demoFixture.longDistance.activities)
    return
  }
  if (!experienceMode.value.hasPairContext) {
    const workspace = loadSoloConnectionWorkspace()
    health.value = workspace.health
    activities.value = workspace.activities
    return
  }
  const pairId = userStore.activePairId
  if (!pairId) return
  try { health.value = await api.getLongDistanceHealth(pairId) } catch {}
  try { const res = await api.getLongDistanceActivities(pairId); activities.value = Array.isArray(res) ? res : [] } catch {}
}

async function createActivity(type) {
  if (experienceMode.value.isDemoMode) {
    activities.value = [
      { id: `ld-demo-${Date.now()}`, activity_type: type, status: 'pending' },
      ...activities.value,
    ]
    showToast('样例里已经加了一次同步安排')
    return
  }
  if (!experienceMode.value.hasPairContext) {
    const workspace = createSoloConnectionActivityEntry(type, longDistanceActivityLabel(type))
    health.value = workspace.health
    activities.value = workspace.activities
    showToast('这个联系安排已经留在你的单人计划里')
    return
  }
  const pairId = userStore.activePairId
  try {
    await api.createLongDistanceActivity(pairId, type, longDistanceActivityLabel(type))
    showToast('同步安排已保存')
    await loadData()
  } catch (e) { showToast(e.message || '同步安排没保存上，请稍后再试') }
}

function activityStatusLabel(activity) {
  if (activity.status === 'completed') return '已完成'
  return experienceMode.value.hasPairContext ? '进行中' : '待推进'
}
</script>

<style scoped>
.ld-score { text-align: center; padding: 16px 0; }
.ld-score__num { font-size: 48px; font-weight: 700; color: var(--warm-600); font-family: var(--font-serif); }
.ld-score__label { font-size: 16px; color: var(--ink-faint); }
.ld-score__summary { margin-top: 10px; color: var(--ink-soft); line-height: 1.7; }
</style>

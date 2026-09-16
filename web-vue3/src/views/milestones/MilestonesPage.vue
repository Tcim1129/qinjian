<template>
  <div class="milestones-page page-shell page-shell--narrow page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">{{ pageEyebrow }}</p>
        <h2>{{ pageTitle }}</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <p class="eyebrow">新建</p>
          <h3>{{ formTitle }}</h3>
        </div>
      </div>
      <form @submit.prevent="handleSubmit" class="form-stack">
        <label class="field">
          <span>类型</span>
          <select v-model="form.type" class="input">
            <option value="anniversary">纪念日</option>
            <option value="proposal">重要承诺</option>
            <option value="wedding">结婚</option>
            <option value="friendship_day">关系起点</option>
            <option value="custom">自定义</option>
          </select>
        </label>
        <label class="field">
          <span>标题</span>
          <input v-model="form.title" class="input" type="text" maxlength="32" :placeholder="titlePlaceholder" />
        </label>
        <label class="field">
          <span>日期</span>
          <input v-model="form.date" class="input" type="date" />
        </label>
        <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
          {{ submitButtonLabel }}
        </button>
      </form>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <p class="eyebrow">时间线</p>
          <h3>{{ listTitle }}</h3>
        </div>
      </div>
      <div v-if="milestones.length" class="stack-list">
        <div v-for="item in milestones" :key="item.id" class="stack-item">
          <div class="stack-item__icon stack-item__icon--gold">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 2.4 5 5.6.8-4 3.9.9 5.5L12 15.6 7.1 18.2 8 12.7 4 8.8l5.6-.8z" stroke-linejoin="round"/></svg>
          </div>
          <div class="stack-item__content">
            <strong>{{ item.title || '未命名' }}</strong>
            <div class="stack-item__meta">{{ milestoneTypeLabel(item.type) }} · {{ formatDate(item.date) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">{{ emptyState }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { milestoneTypeLabel } from '@/utils/displayText'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { createSoloMilestoneEntry, loadSoloMilestoneEntries } from '@/utils/soloWorkspace'

const userStore = useUserStore()
const showToast = inject('showToast')
const milestones = ref([])
const submitting = ref(false)
const form = reactive({ type: 'anniversary', title: '', date: '' })

const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)

const pageEyebrow = computed(() => (experienceMode.value.hasPairContext ? '纪念日' : '重要节点'))
const pageTitle = computed(() => (experienceMode.value.hasPairContext ? '记录重要时刻' : '把值得回看的节点留下来'))
const formTitle = computed(() => (experienceMode.value.hasPairContext ? '添加里程碑' : '添加一个值得回看的节点'))
const listTitle = computed(() => (experienceMode.value.hasPairContext ? '已记录的时刻' : '已留下的节点'))
const titlePlaceholder = computed(() => (experienceMode.value.hasPairContext ? '例如：第一次旅行' : '例如：决定先停一下'))
const emptyState = computed(() => (experienceMode.value.hasPairContext ? '还没有记录重要时刻。' : '还没有留下想回看的节点。'))
const submitButtonLabel = computed(() => {
  if (submitting.value) return '保存中...'
  return experienceMode.value.isDemoMode ? '加入样例' : '保存'
})

onMounted(() => loadMilestones())

async function loadMilestones() {
  if (experienceMode.value.isDemoMode) {
    milestones.value = sortMilestonesByDateDesc(cloneDemo(demoFixture.milestones))
    return
  }
  if (!experienceMode.value.hasPairContext) {
    milestones.value = sortMilestonesByDateDesc(loadSoloMilestoneEntries())
    return
  }
  const pairId = userStore.activePairId
  try { milestones.value = sortMilestonesByDateDesc(await api.getMilestones(pairId)) } catch { milestones.value = [] }
}

async function handleSubmit() {
  if (!form.title || !form.date) { showToast('请填写标题和日期'); return }
  if (experienceMode.value.isDemoMode) {
    milestones.value = [
      {
        id: `milestone-demo-${Date.now()}`,
        type: form.type,
        title: form.title,
        date: form.date,
      },
      ...milestones.value,
    ]
    showToast('样例时间线里已加上这个时刻')
    resetForm()
    return
  }
  if (!experienceMode.value.hasPairContext) {
    milestones.value = createSoloMilestoneEntry({
      type: form.type,
      title: form.title,
      date: form.date,
    })
    showToast('这个节点已经留在你的单人时间线里')
    resetForm()
    return
  }
  const pairId = userStore.activePairId
  submitting.value = true
  try {
    await api.createMilestone(pairId, form.type, form.title, form.date)
    showToast('里程碑已保存')
    resetForm()
    await loadMilestones()
  } catch (e) {
    showToast(e.message || '这次没保存上，请稍后再试')
  } finally { submitting.value = false }
}

function resetForm() {
  form.title = ''
  form.date = ''
}

function formatDate(v) {
  if (!v) return ''
  const d = new Date(v)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function milestoneTime(item) {
  const value = item?.date || item?.milestone_date || item?.created_at || ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 0 : date.getTime()
}

function sortMilestonesByDateDesc(list) {
  return [...(Array.isArray(list) ? list : [])].sort((a, b) => milestoneTime(b) - milestoneTime(a))
}
</script>

<style scoped></style>

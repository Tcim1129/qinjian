<template>
  <div class="coach-page">
    <div class="page-head coach-head">
      <div>
        <p class="eyebrow">缓和建议</p>
        <h2>给彼此一个降温台阶，心软了更好聊~</h2>
      </div>
      <div class="coach-head__actions">
        <button class="btn btn-ghost btn-sm" :disabled="loading" @click="handleLoadProtocol">{{ refreshButtonLabel }}</button>
        <button class="btn btn-secondary btn-sm" :disabled="!protocol" @click="openGeneralAgent">💬 和 AI 商量怎么做</button>
        <button class="btn btn-primary btn-sm" @click="$router.push('/alignment')">{{ alignmentButtonLabel }}</button>
      </div>
    </div>

    <section v-if="protocol" class="protocol-hero">
      <div class="protocol-badge">
        <span>{{ levelLabel }}</span>
      </div>
      <div>
        <p class="eyebrow">当前建议</p>
        <h3>{{ protocol.title }}</h3>
        <p>{{ protocol.summary }}</p>
      </div>
    </section>

    <section v-if="protocol" class="coach-grid">
      <article class="card card-accent" v-for="step in protocol.steps" :key="step.sequence">
        <p class="eyebrow">第 {{ step.sequence }} 步</p>
        <h3>{{ step.title }}</h3>
        <p>{{ step.action }}</p>
        <button class="step-ask-btn" type="button" @click="openStepAgent(step)">问问具体怎么做 ↗</button>
      </article>
    </section>

    <section v-if="protocol" class="coach-lists">
      <article class="card">
        <p class="eyebrow">今天先别做</p>
        <ul class="plain-list">
          <li v-for="item in protocol.do_not" :key="item">{{ item }}</li>
        </ul>
      </article>
      <article class="card">
        <p class="eyebrow">关系开始变稳的信号</p>
        <h3>{{ protocol.success_signal }}</h3>
        <p>{{ protocol.escalation_rule }}</p>
      </article>
    </section>

    <section v-if="protocol" class="coach-lists coach-lists--single">
      <article class="card card-accent coach-card--warning">
        <p class="eyebrow">先照顾自己的边界</p>
        <p>{{ protocol.safety_handoff || protocol.clinical_disclaimer }}</p>
      </article>
    </section>

    <div v-else class="report-empty">
       <strong>{{ loading ? '正在悄悄准备温柔台阶…' : '目前气氛挺好的，还没有需要急救的降温建议哦~' }}</strong>
    </div>
    <ContextAgentDialog v-if="agentContext" :context="agentContext" @close="agentContext = null" />
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import { riskLevelLabel } from '@/utils/displayText'
import { resolveExperienceMode } from '@/utils/experienceMode'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'

const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const protocol = ref(null)
const loading = ref(false)
const agentContext = ref(null)
const protocolRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60 * 1000 })

const experienceMode = computed(() =>
  resolveExperienceMode({
    isDemoMode: userStore.isDemoMode,
    activePairId: userStore.activePairId,
    currentPair: userStore.currentPair,
    pairs: userStore.pairs,
  })
)

const refreshButtonLabel = computed(() => (experienceMode.value.isDemoMode ? '刷新样例' : '重新整理'))
const alignmentButtonLabel = computed(() => {
  if (experienceMode.value.isDemoMode) return '看双视角样例'
  if (experienceMode.value.hasPairContext) return '看双方说法'
  return '看双视角'
})

const levelLabel = computed(() => {
  return riskLevelLabel(protocol.value?.level)
})

onMounted(loadProtocol)

async function loadProtocol() {
  loading.value = true
  try {
    if (experienceMode.value.isDemoMode) {
      protocol.value = cloneDemo(demoFixture.repairProtocol)
      return
    }
    protocol.value = await api.getRepairProtocol(experienceMode.value.activePairId || null)
  } catch (e) {
    protocol.value = null
    showToast(e.message || '缓和建议没整理出来，请稍后再试')
  } finally {
    loading.value = false
  }
}

function handleLoadProtocol() {
  const remainingSeconds = protocolRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`缓和建议整理得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }
  protocolRefreshGuard.markRun()
  return loadProtocol()
}

function openGeneralAgent() {
  if (!protocol.value) return
  agentContext.value = {
    title: '商量缓和方案',
    sourceLabel: `${protocol.value.title || '缓和建议'}${experienceMode.value.isDemoMode ? ' · 样例' : ''}`,
    summary: `当前缓和方案：${protocol.value.title}\n核心建议：${protocol.value.summary}\n今天先别做：${(protocol.value.do_not || []).join('；')}`,
    question: '看着这些缓和步骤，你觉得哪一步最难迈出去？或者需要我帮你起草一句破冰的话吗？~',
    pairId: experienceMode.value.activePairId,
    intent: 'plan',
  }
}

function openStepAgent(step) {
  if (!step) return
  agentContext.value = {
    title: `针对第 ${step.sequence} 步出主意`,
    sourceLabel: `第 ${step.sequence} 步：${step.title}${experienceMode.value.isDemoMode ? ' · 样例' : ''}`,
    summary: `步骤目标：${step.title}\n建议动作：${step.action}`,
    question: `关于“${step.title}”，你想要具体的话术模板，还是担心对方会有什么反应？尽管和我说说看~`,
    pairId: experienceMode.value.activePairId,
    intent: 'wording',
  }
}
</script>

<style scoped>
.coach-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 28px;
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

.protocol-hero {
  position: relative;
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: 18px;
  padding: 22px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at top right, rgba(240, 213, 184, 0.34), transparent 28%),
    linear-gradient(180deg, rgba(255, 252, 247, 0.95), rgba(247, 239, 230, 0.86));
  box-shadow: 0 18px 36px rgba(91, 67, 51, 0.06);
  margin-bottom: 16px;
}
.protocol-hero::before {
  content: "";
  position: absolute;
  left: 22px;
  top: 0;
  width: 80px;
  height: 1px;
  background: linear-gradient(90deg, rgba(215, 104, 72, 0.5), rgba(215, 104, 72, 0));
}

.protocol-badge {
  display: grid;
  place-items: center;
  min-height: 100px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(189, 75, 53, 0.16);
  background: rgba(255, 247, 242, 0.88);
  color: var(--seal-deep);
  text-align: center;
}

.protocol-badge span {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 700;
}

.coach-grid,
.coach-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.coach-grid .card h3,
.coach-lists .card h3 {
  margin-top: 4px;
  font-family: var(--font-serif);
  font-size: 18px;
}

.coach-grid .card p:last-child,
.coach-lists .card p:last-child {
  margin-top: 10px;
  color: var(--ink-soft);
  line-height: 1.72;
}

.coach-lists--single {
  grid-template-columns: minmax(0, 1fr);
}

.coach-card--warning {
  border-color: rgba(189, 75, 53, 0.3);
  background: linear-gradient(180deg, rgba(243, 216, 208, 0.46), rgba(255, 251, 247, 0.84));
}

.plain-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  padding-left: 18px;
  color: var(--ink-soft);
  line-height: 1.65;
}

.report-empty {
  display: grid;
  place-items: center;
  min-height: 220px;
  padding: 28px;
  border: 1px dashed rgba(67, 98, 115, 0.28);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.72);
  text-align: center;
}

@media (max-width: 760px) {
  .coach-head,
  .protocol-hero,
  .coach-grid,
  .coach-lists {
    grid-template-columns: 1fr;
  }

  .coach-head {
    display: grid;
  }
}

@media (max-width: 600px) {
  .coach-page {
    width: min(100% - 20px, var(--content-max));
  }
}

.step-ask-btn {
  margin-top: 12px;
  font-size: 13px;
  color: var(--seal-deep);
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  display: inline-block;
  text-align: left;
}
.step-ask-btn:hover {
  text-decoration: underline;
}
</style>

<template>
  <div class="coach-page page-stack">
    <div class="page-head coach-head">
      <div>
        <p class="eyebrow">判断说明</p>
        <h2>亲健如何整理和判断</h2>
        <p class="methodology-lead">
          这里公开说明系统依据什么数据形成提醒、如何划定风险边界，以及哪些事情不会替你决定。
        </p>
      </div>
      <div class="coach-head__actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/report')">返回简报</button>
        <button class="btn btn-primary btn-sm" type="button" @click="$router.push('/privacy-security')">隐私与安全</button>
      </div>
    </div>

    <section class="card card-accent methodology-overview">
      <div class="methodology-overview__meta">
        <span class="pill pill--soft">{{ scopeLabel }}</span>
        <span class="pill pill--soft">{{ modelFamilyLabel }}</span>
      </div>
      <h3>{{ systemNameLabel }}</h3>
      <p>
        亲健先从日常记录、关系体检和安排反馈里提取可核对的事实信号，再结合规则分层生成提醒和建议；
        所有表达只作相处参考，不替代你和伴侣自己的判断。
      </p>
      <div v-if="currentFocus.length" class="methodology-focus">
        <span class="eyebrow">当前整理节奏</span>
        <div class="methodology-focus__list">
          <span v-for="(step, index) in currentFocus" :key="step" class="methodology-focus__step">
            {{ index + 1 }}. {{ step }}
          </span>
        </div>
      </div>
    </section>

    <section class="methodology-grid">
      <article class="card">
        <p class="eyebrow">输入依据</p>
        <h3>系统参考哪些记录</h3>
        <ul class="plain-list">
          <li v-for="item in measurementModel" :key="item">{{ item }}</li>
        </ul>
      </article>

      <article class="card">
        <p class="eyebrow">判断方式</p>
        <h3>分数与建议怎么形成</h3>
        <ul class="plain-list">
          <li v-for="item in decisionModel" :key="item">{{ item }}</li>
        </ul>
      </article>
    </section>

    <section v-if="theoryCards.length" class="card">
      <div class="card-header">
        <div>
          <p class="eyebrow">方法参考</p>
          <h3>当前启用模块背后的思路</h3>
        </div>
      </div>
      <div class="methodology-theory-grid">
        <article v-for="card in theoryCards" :key="card.id || card.title" class="methodology-theory-item">
          <h4>{{ card.title || card.name || '参考思路' }}</h4>
          <p>{{ card.summary || card.application || card.description }}</p>
        </article>
      </div>
    </section>

    <section class="card methodology-boundary">
      <p class="eyebrow">隐私与使用边界</p>
      <h3>几点明确承诺</h3>
      <ul class="plain-list">
        <li>默认只展示授权范围内的数据：个人记录仅自己可见，双人视角不会直接露出未共享的私密原文。</li>
        <li>关系体检综合分由五个核心维度均衡汇总得出，方便你和历史记录按同一口径回看变化。</li>
        <li>{{ disclaimer }}</li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api'
import { cloneDemo, demoFixture } from '@/demo/fixtures'
import { useUserStore } from '@/stores/user'

const DEFAULT_METHODOLOGY = {
  system_name_label: '亲健关系整理说明',
  model_family_label: '规则分层与反馈校准',
  measurement_model: [
    '每日记录里的情绪感受与互动情况',
    '关系体检五个维度的自评结果与趋势变化',
    '今日安排的完成情况与“后来怎么样”主观反馈',
    '发前看看和双视角功能中的纠错反馈',
  ],
  decision_model: [
    '先核对风险信号，遇到明显情绪紧绷时优先建议降温和暂停争执',
    '核心风险分层由稳定规则控制，不由自由生成文本随意改写',
    '根据实际执行体验和反馈调整后续提醒语气与安排难度',
    '涉及账号删除、记忆停用或新增安排时，先展示内容再由用户手动确认',
  ],
  current_focus: ['先稳住当下情绪', '再对齐彼此理解', '最后落一个小而具体的行动'],
  theory_basis: [],
  disclaimer: '亲健参考关系心理学与行为科学整理相处建议，不属于医疗诊断、临床治疗或专业心理测评。',
}

const userStore = useUserStore()
const methodology = ref(cloneDemo(DEFAULT_METHODOLOGY))

const activePairId = computed(() => userStore.activePairId || null)
const scopeLabel = computed(() => {
  if (userStore.isDemoMode) return '体验样例说明'
  return activePairId.value ? '当前双人关系视角' : '当前个人记录视角'
})
const systemNameLabel = computed(() =>
  methodology.value?.system_name_label || methodology.value?.system_name || DEFAULT_METHODOLOGY.system_name_label
)
const modelFamilyLabel = computed(() =>
  methodology.value?.model_family_label || methodology.value?.model_family || DEFAULT_METHODOLOGY.model_family_label
)
const measurementModel = computed(() =>
  methodology.value?.measurement_model?.length ? methodology.value.measurement_model : DEFAULT_METHODOLOGY.measurement_model
)
const decisionModel = computed(() =>
  methodology.value?.decision_model?.length ? methodology.value.decision_model : DEFAULT_METHODOLOGY.decision_model
)
const currentFocus = computed(() =>
  methodology.value?.current_focus?.length ? methodology.value.current_focus : DEFAULT_METHODOLOGY.current_focus
)
const theoryCards = computed(() =>
  Array.isArray(methodology.value?.theory_basis) ? methodology.value.theory_basis : []
)
const disclaimer = computed(() =>
  methodology.value?.disclaimer || DEFAULT_METHODOLOGY.disclaimer
)

onMounted(async () => {
  if (userStore.isDemoMode) {
    methodology.value = {
      ...cloneDemo(DEFAULT_METHODOLOGY),
      ...cloneDemo(demoFixture.methodology || {}),
      system_name_label: demoFixture.methodology?.system_name || DEFAULT_METHODOLOGY.system_name_label,
      model_family_label: demoFixture.methodology?.model_family || DEFAULT_METHODOLOGY.model_family_label,
    }
    return
  }
  try {
    const response = await api.getMethodology(activePairId.value)
    if (response && typeof response === 'object') {
      methodology.value = {
        ...cloneDemo(DEFAULT_METHODOLOGY),
        ...response,
      }
    }
  } catch {
    methodology.value = cloneDemo(DEFAULT_METHODOLOGY)
  }
})
</script>

<style scoped>
.coach-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 32px;
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

.methodology-lead {
  margin-top: 8px;
  color: var(--ink-soft);
  line-height: 1.7;
  max-width: 640px;
}

.methodology-overview {
  display: grid;
  gap: 12px;
}

.methodology-overview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.methodology-overview h3 {
  font-family: var(--font-serif);
  font-size: 22px;
}

.methodology-overview p {
  color: var(--ink-soft);
  line-height: 1.75;
}

.methodology-focus {
  display: grid;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.methodology-focus__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.methodology-focus__step {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 250, 244, 0.9);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--ink);
}

.methodology-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.methodology-grid h3,
.methodology-boundary h3 {
  margin-top: 4px;
  font-family: var(--font-serif);
  font-size: 18px;
}

.plain-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding-left: 18px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.methodology-theory-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.methodology-theory-item {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: rgba(255, 252, 247, 0.86);
}

.methodology-theory-item h4 {
  font-size: 15px;
  color: var(--ink);
}

.methodology-theory-item p {
  margin-top: 6px;
  font-size: 13px;
  color: var(--ink-soft);
  line-height: 1.65;
}

.methodology-boundary {
  border-color: rgba(67, 98, 115, 0.24);
  background: rgba(255, 252, 247, 0.9);
}

@media (max-width: 760px) {
  .coach-head,
  .methodology-grid,
  .methodology-theory-grid {
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
</style>

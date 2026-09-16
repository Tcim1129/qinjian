<template>
  <div class="membership-page page-shell page-shell--wide page-stack">
    <div class="page-head membership-head">
      <div>
        <p class="eyebrow">会员</p>
        <h2>想看更细的周报和趋势</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>

    <div class="pricing-grid">
      <article v-for="plan in plans" :key="plan.name" class="card pricing-card" :class="{ 'pricing-card--featured': plan.featured }">
        <span class="pill" :class="plan.pillClass">{{ plan.tier }}</span>
        <h3>{{ plan.name }}</h3>
        <strong>{{ plan.price }}<span>{{ plan.unit }}</span></strong>
        <p>{{ plan.desc }}</p>
        <div class="pricing-card__summary">
          <span>你会拿到</span>
          <strong>{{ plan.deliver }}</strong>
        </div>
        <ul class="pricing-features">
          <li v-for="feature in plan.features" :key="feature">{{ feature }}</li>
        </ul>
        <button class="btn btn-block btn-sm" :class="plan.buttonClass" type="button" @click="activePlan = plan">
          {{ plan.button }}
        </button>
      </article>
    </div>

    <div v-if="activePlan" class="service-modal" role="dialog" aria-modal="true" @click.self="activePlan = null">
      <section class="service-modal__paper">
        <p class="eyebrow">{{ activePlan.tier }}</p>
        <h3>{{ activePlan.name }}</h3>
        <strong class="modal-price">{{ activePlan.price }}{{ activePlan.unit }}</strong>
        <div class="service-modal__detail">
          <span>适合谁</span>
          <strong>{{ activePlan.fit }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>你会拿到</span>
          <strong>{{ activePlan.deliver }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>开通后可立即使用</span>
          <strong>{{ activePlan.instantUse }}</strong>
        </div>
        <div class="service-modal__list">
          <span v-for="item in activePlan.features" :key="item">{{ item }}</span>
        </div>
        <div class="hero-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="activePlan = null">知道了</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activePlan = ref(null)

const plans = [
  {
    tier: '免费版',
    name: '基础记录',
    price: '¥0',
    unit: '',
    desc: '记录、日报和关系树。',
    fit: '适合：刚开始使用亲健。',
    deliver: '基础记录、基础日报和关系树成长。',
    instantUse: '记录今天发生的事。',
    button: '免费使用',
    buttonClass: 'btn-ghost',
    pillClass: '',
    features: ['基础记录', '基础日报', '关系树成长'],
  },
  {
    tier: '进阶版',
    name: '深度周报',
    price: '¥29',
    unit: '/月',
    desc: '每周看一次趋势和反复问题。',
    fit: '适合：想稳定复盘一段关系。',
    deliver: '每周趋势、重复问题提醒和每日提醒建议。',
    instantUse: '查看周报、趋势和提醒。',
    button: '查看深度周报包含什么',
    buttonClass: 'btn-primary',
    pillClass: 'pill-warning',
    featured: true,
    features: ['深度周报', '趋势汇总', '每日提醒建议', '重点提醒'],
  },
  {
    tier: '年度版',
    name: '持续记录方案',
    price: '¥199',
    unit: '/年',
    desc: '持续报告、课程和支持入口。',
    fit: '适合：希望持续经营关系。',
    deliver: '完整报告、课程入口、活动建议和咨询入口。',
    instantUse: '报告、课程和支持入口。',
    button: '查看年度方案',
    buttonClass: 'btn-secondary',
    pillClass: 'pill-success',
    features: ['完整报告', '课程入口', '活动建议', '咨询入口'],
  },
]
</script>

<style scoped>
.pricing-grid {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
}

.membership-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.membership-note {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  margin: 0 auto;
  padding: 14px 0;
  border-top: 1px solid var(--border-strong);
  border-bottom: 1px solid var(--border-strong);
}

.membership-note span {
  padding: 4px 9px;
  border: 1px solid rgba(189, 75, 53, 0.22);
  border-radius: var(--radius-md);
  background: var(--seal-soft);
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 800;
}

.membership-note p {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.7;
}

.membership-note strong {
  color: var(--sky-deep);
  font-size: 14px;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.pricing-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  min-height: 330px;
  padding: 24px 20px;
}
.pricing-card h3 {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 700;
}
.pricing-card strong {
  font-size: 32px;
  font-weight: 700;
  color: var(--seal-deep);
  font-family: var(--font-serif);
}
.pricing-card strong span {
  font-size: 14px;
  font-weight: 400;
  color: var(--ink-faint);
}
.pricing-card p {
  font-size: 13px;
  color: var(--ink-soft);
  line-height: 1.65;
}
.pricing-fit {
  color: var(--sky-deep);
  font-size: 12px;
  font-weight: 800;
}
.pricing-card__summary {
  display: grid;
  gap: 4px;
}
.pricing-card__summary span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}
.pricing-card__summary strong {
  color: var(--ink);
  font-size: 13px;
  line-height: 1.6;
}
.pricing-features {
  flex: 1;
  display: grid;
  gap: 7px;
  margin: 4px 0 2px;
  padding: 0;
  list-style: none;
}
.pricing-features li {
  position: relative;
  padding-left: 14px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.55;
}
.pricing-features li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--seal);
}
.pricing-card--featured {
  border: 2px solid rgba(189, 75, 53, 0.32);
  background:
    linear-gradient(180deg, rgba(255, 244, 239, 0.94), rgba(255, 251, 247, 0.86));
  position: relative;
}

.service-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(44, 48, 39, 0.28);
}

.service-modal__paper {
  width: min(440px, 100%);
  max-height: min(80vh, 720px);
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 22px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: var(--paper);
}

.service-modal__paper h3 {
  margin: 4px 0 10px;
  font-family: var(--font-serif);
  font-size: 23px;
}

.modal-price {
  display: block;
  margin-bottom: 14px;
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 30px;
}

.service-modal__detail {
  display: grid;
  gap: 4px;
  margin-bottom: 14px;
}

.service-modal__detail span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}

.service-modal__detail strong {
  color: var(--ink);
  line-height: 1.7;
}

.service-modal__list {
  display: grid;
  gap: 8px;
  margin: 16px 0;
}

.service-modal__list span {
  padding: 9px 10px;
  border: 1px solid rgba(67, 98, 115, 0.18);
  border-radius: var(--radius-md);
  background: rgba(232, 240, 244, 0.86);
  color: var(--sky-deep);
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 520px) {
  .membership-head {
    flex-direction: column;
  }
  .membership-note {
    display: none;
  }
}
</style>

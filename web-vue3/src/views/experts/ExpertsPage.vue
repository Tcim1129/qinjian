<template>
  <div class="experts-page page-shell page-shell--wide page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">聊聊</p>
        <h2>约一次关系梳理</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">回总览</button>
    </div>

    <div class="expert-grid">
      <article v-for="item in experts" :key="item.name" class="card expert-card">
        <div class="expert-card__avatar">{{ item.name[0] }}</div>
        <h3>{{ item.name }}</h3>
        <p>{{ item.focus }}</p>
        <div class="expert-card__meta">
          <span class="pill">{{ item.title }}</span>
        </div>
        <button class="btn btn-secondary btn-sm" type="button" @click="activeExpert = item">查看这位老师能帮什么</button>
      </article>
    </div>

    <div v-if="activeExpert" class="service-modal" role="dialog" aria-modal="true" @click.self="activeExpert = null">
      <section class="service-modal__paper">
        <p class="eyebrow">聊聊</p>
        <h3>{{ activeExpert.name }}</h3>
        <p>{{ activeExpert.focus }}</p>
        <div class="service-modal__detail">
          <span>适合谁</span>
          <strong>{{ activeExpert.fit }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>可带来</span>
          <strong>{{ activeExpert.bring }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>带走</span>
          <strong>{{ activeExpert.leaveWith }}</strong>
        </div>
        <div class="service-modal__list">
          <span>{{ activeExpert.title }}</span>
          <span>{{ activeExpert.deliver }}</span>
          <span>{{ activeExpert.note }}</span>
        </div>
        <div class="hero-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="activeExpert = null">知道了</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeExpert = ref(null)

const experts = [
  {
    name: '张心怡',
    focus: '婚恋沟通、关系缓和、情绪共情训练',
    title: '国家二级心理咨询师',
    fit: '高频争吵后的缓和复盘。',
    deliver: '20 分钟体验梳理。',
    bring: '最近一次争吵记录、卡住的原话，或一份简报。',
    leaveWith: '问题梳理、优先级判断，以及下一步怎么开口。',
    note: '首次更适合先做一次关系议题梳理，再决定要不要继续深入。',
  },
  {
    name: '李明辉',
    focus: '家庭关系、亲子协作、夫妻沟通策略',
    title: '家庭治疗师',
    fit: '家庭议题和长期协作卡点。',
    deliver: '20 分钟家庭关系梳理。',
    bring: '一段最近的家庭冲突、长期分工难题，或你最想先解决的一件事。',
    leaveWith: '问题范围、优先级排序和更容易推进的下一步动作。',
    note: '如果你们最近一直在同一个问题上兜圈，这类梳理会更合适。',
  },
  {
    name: '王婷婷',
    focus: '年轻人恋爱教练、自我成长与关系边界',
    title: '情感教练',
    fit: '边界表达和恋爱节奏调整。',
    deliver: '20 分钟行动型梳理。',
    bring: '一段说不出口的话、最近的节奏困扰，或想确认边界的场景。',
    leaveWith: '更适合你的表达方式，以及一次能落地的小调整。',
    note: '更偏行动陪练，不替代临床诊断。',
  },
]
</script>

<style scoped>
.expert-grid {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
}
.expert-note {
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
.expert-note span {
  padding: 4px 9px;
  border: 1px solid rgba(67, 98, 115, 0.18);
  border-radius: var(--radius-md);
  background: rgba(232, 240, 244, 0.86);
  color: var(--sky-deep);
  font-size: 12px;
  font-weight: 800;
}
.expert-note p {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.7;
}
.expert-note strong {
  color: var(--seal-deep);
  font-size: 14px;
}
.page-head--split {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.expert-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.expert-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  min-height: 280px;
}
.expert-card__avatar {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  display: grid;
  place-items: center;
  border: 1px solid rgba(189, 75, 53, 0.28);
  background: var(--seal-soft);
  color: var(--seal-deep);
  font-size: 22px;
  font-weight: 700;
}
.expert-card h3 {
  font-family: var(--font-serif);
  font-size: 20px;
}
.expert-card p {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.6;
}
.expert-card__meta {
  flex: 1;
  display: grid;
  gap: 8px;
  align-content: start;
  justify-items: center;
}
.expert-card__meta small {
  max-width: 21ch;
  color: var(--sky-deep);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.55;
}
@media (max-width: 520px) {
  .page-head--split { flex-direction: column; }
  .expert-note {
    display: none;
  }
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

.service-modal__paper p {
  color: var(--ink-soft);
  line-height: 1.6;
}

.service-modal__detail {
  display: grid;
  gap: 4px;
  margin-top: 14px;
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
</style>

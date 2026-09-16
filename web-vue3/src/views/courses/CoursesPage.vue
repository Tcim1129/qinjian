<template>
  <div class="courses-page page-shell page-shell--wide page-stack">
    <div class="page-head page-head--split">
      <div>
        <p class="eyebrow">课程</p>
        <h2>开始学沟通</h2>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/discover')">返回</button>
    </div>

    <div class="content-grid">
      <article v-for="item in courses" :key="item.title" class="card content-card">
        <span class="pill">{{ item.tag }}</span>
        <h3>{{ item.title }}</h3>
        <p>{{ item.desc }}</p>
        <div class="content-card__block">
          <span>适合谁</span>
          <strong>{{ item.fit }}</strong>
        </div>
        <div class="content-card__block">
          <span>你会拿到</span>
          <strong>{{ item.takeaway }}</strong>
        </div>
        <div class="content-card__block">
          <span>交付内容</span>
          <strong>{{ item.delivery }}</strong>
        </div>
        <ul>
          <li v-for="point in item.points" :key="point">{{ point }}</li>
        </ul>
        <button class="btn btn-ghost btn-sm" type="button" @click="activeCourse = item">查看这一课能解决什么</button>
      </article>
    </div>

    <div v-if="activeCourse" class="service-modal" role="dialog" aria-modal="true" @click.self="activeCourse = null">
      <section class="service-modal__paper">
        <p class="eyebrow">{{ activeCourse.tag }}</p>
        <h3>{{ activeCourse.title }}</h3>
        <p>{{ activeCourse.desc }}</p>
        <div class="service-modal__summary">
          <span>学完带走</span>
          <strong>{{ activeCourse.gain }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>适合谁</span>
          <strong>{{ activeCourse.fit }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>包含</span>
          <strong>{{ activeCourse.takeaway }}</strong>
        </div>
        <div class="service-modal__detail">
          <span>交付内容</span>
          <strong>{{ activeCourse.delivery }}</strong>
        </div>
        <div class="service-modal__list">
          <span v-for="point in activeCourse.points" :key="point">{{ point }}</span>
        </div>
        <div class="hero-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="activeCourse = null">知道了</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeCourse = ref(null)

const courses = [
  {
    tag: '沟通',
    title: '把指责换成表达',
    desc: '想把委屈说清楚，又不想一开口就变成争论。',
    fit: '想把委屈说清楚，但不想一开口就吵起来。',
    takeaway: '事实描述模板、需求表达模板、缓和收尾句。',
    delivery: '3 个场景拆解 + 1 组可直接照着说的句子。',
    gain: '你会更稳地开口，也更容易把真正想说的话说完。',
    points: ['观察事实，不急着下结论', '把自己的需求说清楚', '用缓和的话收尾'],
  },
  {
    tag: '缓和',
    title: '吵完以后怎么回来',
    desc: '如果总是停在“算了吧”，这一课会把暂停、回看和重新开口连成一个完整流程。',
    fit: '高频争吵后想缓和，但每次都不知道该怎么重新开始。',
    takeaway: '暂停节点识别、回看提纲、重新开口的第一句。',
    delivery: '争吵复盘框架 + 2 个回到对话的起手式。',
    gain: '你会更知道什么时候该停，什么时候可以把关系往回拉一点。',
    points: ['识别争吵变激烈的节点', '学会暂停和回到对话', '把回看落到具体行动'],
  },
  {
    tag: '成长',
    title: '靠近，也保留边界',
    desc: '需要重新对齐节奏时，这一课会把“靠近”和“保留边界”放到一张图里看清楚。',
    fit: '亲密关系、朋友关系和家庭关系里需要重新对齐节奏的时候。',
    takeaway: '边界说法、共同目标梳理方式、低压力靠近动作。',
    delivery: '边界对齐清单 + 1 份可带走的关系节奏卡。',
    gain: '你会更清楚什么该答应、什么该拒绝，以及怎么把关系留在舒服的位置。',
    points: ['梳理双方的边界', '建立共同的目标', '保持稳定的陪伴节奏'],
  },
]
</script>

<style scoped>
.content-grid {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
}
.course-note {
  width: 100%;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  margin: 0 auto;
  padding: 14px 0;
  border-top: 1px solid var(--border-strong);
  border-bottom: 1px solid var(--border-strong);
}
.course-note span {
  padding: 4px 9px;
  border: 1px solid rgba(91, 141, 238, 0.22);
  border-radius: var(--radius-md);
  background: var(--lively-blue-soft);
  color: var(--sky-deep);
  font-size: 12px;
  font-weight: 800;
}
.course-note strong {
  color: var(--ink);
  font-size: 14px;
}
.course-note p {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.7;
}
.page-head--split {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.content-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  min-height: 300px;
}
.content-card h3 {
  font-family: var(--font-serif);
  font-size: 20px;
}
.content-card p {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.6;
}
.content-card__block {
  display: grid;
  gap: 4px;
}
.content-card__block span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}
.content-card__block strong {
  color: var(--ink);
  font-size: 13px;
  line-height: 1.6;
}
.content-card ul {
  flex: 1;
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.content-card li {
  position: relative;
  padding-left: 14px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.58;
}
.content-card li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--seal);
}
@media (max-width: 520px) {
  .page-head--split { flex-direction: column; }
  .course-note {
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

.service-modal__summary,
.service-modal__detail {
  display: grid;
  gap: 4px;
  margin-top: 14px;
}

.service-modal__summary span,
.service-modal__detail span {
  color: var(--ink-faint);
  font-size: 12px;
  font-weight: 800;
}

.service-modal__summary strong,
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

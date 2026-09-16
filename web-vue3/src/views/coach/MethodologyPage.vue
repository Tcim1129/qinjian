<template>
  <div class="coach-page">
    <div class="page-head coach-head">
      <div>
        <p class="eyebrow">未开放</p>
        <h2>这部分暂不开放</h2>
        <p>请先回到首页或今日练习。</p>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$router.push('/')">返回首页</button>
    </div>

    <section class="card card-accent methodology-card">
      <p>首页和今日练习已经可用。</p>
    </section>
  </div>
</template>

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
  margin-bottom: 16px;
}

.methodology-card {
  color: var(--ink-soft);
  line-height: 1.7;
}

@media (max-width: 760px) {
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

<template>
  <view class="report-page">
    <!-- 顶部标题卡片 -->
    <view class="header-card">
      <view class="header-row">
        <text class="page-title">双人共鸣简报</text>
        <view class="pair-tag-badge">
          <text>{{ userStore.partnerName || '林夏' }} 的空间</text>
        </view>
      </view>
      <text class="page-sub">基于双方日常记录与情感频率，由亲健 AI 深度复盘</text>
    </view>

    <!-- 简报周期分段器 -->
    <view class="segmented-tabs">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-item', activeTab === tab.key ? 'active' : '']"
        @click="activeTab = tab.key"
      >
        <text class="tab-label">{{ tab.label }}</text>
      </view>
    </view>

    <!-- 日报视图 -->
    <view v-if="activeTab === 'daily'" class="report-body">
      <view class="content-card">
        <view class="score-hero">
          <view class="score-ring">
            <text class="score-number">{{ dailyReport.health_score }}</text>
            <text class="score-text">健康分</text>
          </view>
          <view class="score-detail">
            <text class="score-status">{{ getStatusText(dailyReport.health_score) }}</text>
            <text class="score-date">{{ todayDate }}</text>
            <text class="score-note">双方今日互动频率舒适，情绪感知处于良性共振状态</text>
          </view>
        </view>

        <view class="section-block">
          <text class="section-title">今日核心摘要</text>
          <text class="section-desc">{{ dailyReport.summary }}</text>
        </view>

        <view class="section-block">
          <text class="section-title">敏锐观察</text>
          <view class="bullet-list">
            <view
              v-for="(item, idx) in dailyReport.observations"
              :key="idx"
              class="bullet-row"
            >
              <text class="bullet-dot">•</text>
              <text class="bullet-text">{{ item }}</text>
            </view>
          </view>
        </view>

        <view class="section-block">
          <text class="section-title">今日微小温暖动作</text>
          <view class="action-suggestions">
            <view
              v-for="(sug, idx) in dailyReport.suggestions"
              :key="idx"
              class="suggestion-pill"
            >
              <text class="pill-num">{{ idx + 1 }}</text>
              <text class="pill-text">{{ sug }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 周报视图 -->
    <view v-else-if="activeTab === 'weekly'" class="report-body">
      <view class="content-card">
        <text class="section-title">本周健康趋势波动</text>
        <view class="trend-chart-box">
          <view
            v-for="(day, idx) in weeklyReport.daily_scores"
            :key="idx"
            class="chart-col"
          >
            <view class="bar-track">
              <view
                class="bar-filled"
                :style="{ height: `${(day.score / 100) * 160}rpx` }"
              ></view>
            </view>
            <text class="bar-score">{{ day.score }}</text>
            <text class="bar-day">{{ day.label }}</text>
          </view>
        </view>

        <view class="section-block">
          <text class="section-title">本周关系态势分析</text>
          <text class="section-desc">{{ weeklyReport.summary }}</text>
        </view>

        <view class="stats-overview-grid">
          <view class="metric-box">
            <text class="metric-val">{{ weeklyReport.checkin_days }} 天</text>
            <text class="metric-key">打卡记录</text>
          </view>
          <view class="metric-box">
            <text class="metric-val">{{ weeklyReport.interaction_count }} 次</text>
            <text class="metric-key">互动沟通</text>
          </view>
          <view class="metric-box">
            <text class="metric-val">{{ weeklyReport.avg_feeling }}</text>
            <text class="metric-key">平均心境分</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 月报视图 -->
    <view v-else class="report-body">
      <view class="content-card">
        <view class="section-block">
          <text class="section-title">月度关系深度复盘</text>
          <text class="section-desc">{{ monthlyReport.summary }}</text>
        </view>

        <view class="section-block">
          <text class="section-title">月度高光时刻</text>
          <view class="highlight-list">
            <view
              v-for="(hl, idx) in monthlyReport.highlights"
              :key="idx"
              class="highlight-card"
            >
              <text class="hl-date">{{ hl.date }}</text>
              <text class="hl-content">{{ hl.content }}</text>
            </view>
          </view>
        </view>

        <view class="growth-box">
          <text class="growth-badge">✨ 关系成长感悟</text>
          <text class="growth-text">{{ monthlyReport.growth }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const activeTab = ref('daily')
const tabs = [
  { key: 'daily', label: '日报' },
  { key: 'weekly', label: '周报' },
  { key: 'monthly', label: '月报' }
]

const todayDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日`
})

const dailyReport = ref({
  health_score: 88,
  summary: '今天你们进行了深度自然的沟通，双方都坦诚表达了真实想法。整体氛围温润，关系健康度处于高舒适期。',
  observations: [
    '下班后主动分享了生活细节，消解了一整天的疲惫感',
    '双方在面对工作压力时互给空间，未将负面情绪迁怒于彼此',
    '情绪共鸣自然真诚，对周末日程达成了初步默契'
  ],
  suggestions: [
    '晚上睡前留出 15 分钟温和对齐，不谈复杂规划',
    '明天尝试给对方带一份微小的小惊喜或热饮',
    '继续保持疲惫时先深呼吸、给彼此留白的习惯'
  ]
})

const weeklyReport = ref({
  daily_scores: [
    { label: '一', score: 78 },
    { label: '二', score: 82 },
    { label: '三', score: 85 },
    { label: '四', score: 80 },
    { label: '五', score: 90 },
    { label: '六', score: 94 },
    { label: '日', score: 88 }
  ],
  summary: '本周关系整体稳定向好，互动质量显著提升。周末的深度长谈帮助双方彻底解开了近期的分工困惑。',
  checkin_days: 7,
  interaction_count: 24,
  avg_feeling: 8.5
})

const monthlyReport = ref({
  summary: '本月关系保持高质量发展，双方在表达需求和倾听彼此上有明显进阶。面对分歧时能够先看见情绪再解决问题，互相包容度极高。',
  highlights: [
    { date: '9月5日', content: '共同完成了关于未来工作与居住规划的深层沟通' },
    { date: '9月14日', content: '在双方均面临加班压力时，默契给予安静陪伴' },
    { date: '9月21日', content: '达成 100 天连续记录里程碑' }
  ],
  growth: '本月最大的进步是在疲惫和分歧时能够先给彼此 20 分钟冷静期，不再急于用指责证明对错。这是关系迈向成熟最宝贵的基石。'
})

function getStatusText(score) {
  if (score >= 85) return '极佳 · 高度默契'
  if (score >= 70) return '良好 · 节奏舒适'
  return '平稳 · 需多留白'
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.report-page {
  min-height: 100vh;
  padding: 24rpx 32rpx 60rpx;
  box-sizing: border-box;
}

.header-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 28rpx;
  margin-bottom: 24rpx;
  box-shadow: $shadow-sm;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-family: $font-serif;
  font-size: 40rpx;
  font-weight: 800;
  color: $color-ink;
}

.pair-tag-badge {
  font-size: 22rpx;
  font-weight: 700;
  color: $color-moss-deep;
  background: $color-moss-soft;
  padding: 6rpx 18rpx;
  border-radius: 12rpx;
}

.page-sub {
  font-size: 24rpx;
  color: $color-ink-faint;
  margin-top: 8rpx;
  display: block;
}

.segmented-tabs {
  display: flex;
  background: rgba(245, 238, 231, 0.74);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 16rpx;
  padding: 6rpx;
  margin-bottom: 28rpx;
}

.tab-item {
  flex: 1;
  height: 68rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  transition: all 0.2s ease;

  &.active {
    background: #fffdfa;
    box-shadow: 0 4rpx 14rpx rgba(74, 52, 36, 0.08);

    .tab-label {
      color: $color-seal-deep;
      font-weight: 800;
    }
  }
}

.tab-label {
  font-size: 28rpx;
  color: $color-ink-soft;
  font-weight: 600;
}

.content-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 32rpx;
  box-shadow: $shadow-sm;
}

.score-hero {
  display: flex;
  align-items: center;
  gap: 28rpx;
  padding-bottom: 30rpx;
  border-bottom: 1px solid rgba(68, 52, 40, 0.1);
  margin-bottom: 28rpx;
}

.score-ring {
  width: 150rpx;
  height: 150rpx;
  border-radius: 50%;
  background: rgba(95, 135, 111, 0.15);
  border: 4rpx solid $color-moss;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-number {
  font-family: $font-serif;
  font-size: 56rpx;
  font-weight: 800;
  color: $color-moss;
  line-height: 1;
}

.score-text {
  font-size: 20rpx;
  color: $color-ink-soft;
  margin-top: 4rpx;
}

.score-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.score-status {
  font-size: 30rpx;
  font-weight: 800;
  color: $color-ink;
}

.score-date {
  font-size: 22rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
}

.score-note {
  font-size: 22rpx;
  color: $color-ink-soft;
  margin-top: 8rpx;
  line-height: 1.4;
}

.section-block {
  margin-bottom: 28rpx;
}

.section-title {
  font-family: $font-serif;
  font-size: 28rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
  margin-bottom: 12rpx;
}

.section-desc {
  font-size: 26rpx;
  color: $color-ink-soft;
  line-height: 1.6;
  background: rgba(246, 240, 234, 0.6);
  padding: 20rpx;
  border-radius: 12rpx;
  display: block;
}

.bullet-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.bullet-row {
  display: flex;
  align-items: flex-start;
  gap: 10rpx;
}

.bullet-dot {
  color: $color-seal;
  font-size: 26rpx;
  line-height: 1.5;
}

.bullet-text {
  flex: 1;
  font-size: 24rpx;
  color: $color-ink;
  line-height: 1.5;
}

.action-suggestions {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.suggestion-pill {
  display: flex;
  align-items: center;
  gap: 14rpx;
  background: rgba(215, 104, 72, 0.08);
  border: 1px solid rgba(215, 104, 72, 0.2);
  padding: 14rpx 20rpx;
  border-radius: 12rpx;
}

.pill-num {
  width: 36rpx;
  height: 36rpx;
  border-radius: 50%;
  background: $color-seal;
  color: #fffdfa;
  font-size: 20rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pill-text {
  font-size: 24rpx;
  color: $color-ink;
  font-weight: 600;
}

/* 趋势图表 */
.trend-chart-box {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 30rpx 10rpx 20rpx;
  height: 240rpx;
}

.chart-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.bar-track {
  width: 24rpx;
  height: 160rpx;
  background: rgba(246, 240, 234, 0.8);
  border-radius: 12rpx;
  display: flex;
  align-items: flex-end;
}

.bar-filled {
  width: 100%;
  background: $color-moss;
  border-radius: 12rpx;
  transition: height 0.3s ease;
}

.bar-score {
  font-size: 18rpx;
  color: $color-ink-faint;
  font-weight: 600;
}

.bar-day {
  font-size: 22rpx;
  color: $color-ink-soft;
}

.stats-overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-top: 20rpx;
}

.metric-box {
  background: rgba(246, 240, 234, 0.6);
  border-radius: 14rpx;
  padding: 20rpx 10rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.metric-val {
  font-family: $font-serif;
  font-size: 32rpx;
  font-weight: 800;
  color: $color-seal-deep;
}

.metric-key {
  font-size: 20rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
}

.highlight-list {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.highlight-card {
  background: rgba(246, 240, 234, 0.6);
  border-radius: 12rpx;
  padding: 18rpx 20rpx;
}

.hl-date {
  font-size: 20rpx;
  color: $color-seal-deep;
  font-weight: 700;
  display: block;
}

.hl-content {
  font-size: 24rpx;
  color: $color-ink;
  margin-top: 4rpx;
  display: block;
}

.growth-box {
  background: rgba(240, 213, 184, 0.45);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 14rpx;
  padding: 24rpx;
}

.growth-badge {
  font-size: 24rpx;
  font-weight: 800;
  color: $color-seal-deep;
  display: block;
  margin-bottom: 8rpx;
}

.growth-text {
  font-size: 24rpx;
  color: $color-ink;
  line-height: 1.6;
}
</style>

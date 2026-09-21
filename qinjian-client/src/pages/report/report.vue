<template>
  <view class="container">
    <view class="header">
      <text class="title">关系简报</text>
    </view>

    <view class="tabs">
      <view 
        v-for="tab in tabs" 
        :key="tab.key"
        :class="['tab', activeTab === tab.key ? 'active' : '']"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- 日报 -->
    <view v-if="activeTab === 'daily'" class="report-content">
      <view v-if="dailyReport" class="report-card">
        <view class="score-section">
          <view class="score-circle">
            <text class="score-value">{{ dailyReport.health_score }}</text>
            <text class="score-label">健康分</text>
          </view>
          <view class="score-desc">
            <text class="status">{{ getStatusText(dailyReport.health_score) }}</text>
            <text class="date">{{ todayDate }}</text>
          </view>
        </view>

        <view class="section">
          <text class="section-title">今日摘要</text>
          <text class="section-content">{{ dailyReport.summary }}</text>
        </view>

        <view class="section">
          <text class="section-title">关键观察</text>
          <view class="observation-list">
            <view 
              v-for="(item, index) in dailyReport.observations" 
              :key="index"
              class="observation-item"
            >
              <text class="bullet">•</text>
              <text class="text">{{ item }}</text>
            </view>
          </view>
        </view>

        <view class="section">
          <text class="section-title">建议动作</text>
          <view class="action-list">
            <view 
              v-for="(action, index) in dailyReport.suggestions" 
              :key="index"
              class="action-item"
            >
              <text class="number">{{ index + 1 }}</text>
              <text class="text">{{ action }}</text>
            </view>
          </view>
        </view>
      </view>

      <view v-else class="empty">
        <text class="text">今天还没有记录</text>
        <button @click="goCheckin" size="mini" type="primary">去记录</button>
      </view>
    </view>

    <!-- 周报 -->
    <view v-if="activeTab === 'weekly'" class="report-content">
      <view v-if="weeklyReport" class="report-card">
        <view class="trend-section">
          <text class="trend-title">本周健康趋势</text>
          <view class="trend-chart">
            <view 
              v-for="(day, index) in weeklyReport.daily_scores" 
              :key="index"
              class="chart-bar"
            >
              <view 
                class="bar"
                :style="{ height: (day.score / 100 * 200) + 'rpx' }"
              ></view>
              <text class="bar-label">{{ day.label }}</text>
            </view>
          </view>
        </view>

        <view class="section">
          <text class="section-title">本周关系状态</text>
          <text class="section-content">{{ weeklyReport.summary }}</text>
        </view>

        <view class="section">
          <text class="section-title">本周互动情况</text>
          <view class="stats-grid">
            <view class="stat-item">
              <text class="stat-value">{{ weeklyReport.checkin_days }}</text>
              <text class="stat-label">记录天数</text>
            </view>
            <view class="stat-item">
              <text class="stat-value">{{ weeklyReport.interaction_count }}</text>
              <text class="stat-label">互动次数</text>
            </view>
            <view class="stat-item">
              <text class="stat-value">{{ weeklyReport.avg_feeling }}</text>
              <text class="stat-label">平均感受</text>
            </view>
            <view class="stat-item">
              <text class="stat-value">{{ weeklyReport.conflict_count }}</text>
              <text class="stat-label">冲突次数</text>
            </view>
          </view>
        </view>

        <view class="section">
          <text class="section-title">下周建议</text>
          <view class="action-list">
            <view 
              v-for="(action, index) in weeklyReport.suggestions" 
              :key="index"
              class="action-item"
            >
              <text class="number">{{ index + 1 }}</text>
              <text class="text">{{ action }}</text>
            </view>
          </view>
        </view>
      </view>

      <view v-else class="empty">
        <text class="text">本周还没有足够的数据</text>
      </view>
    </view>

    <!-- 月报 -->
    <view v-if="activeTab === 'monthly'" class="report-content">
      <view v-if="monthlyReport" class="report-card">
        <view class="month-header">
          <text class="month-title">{{ currentMonth }}</text>
          <view class="month-stats">
            <view class="month-stat">
              <text class="value">{{ monthlyReport.avg_score }}</text>
              <text class="label">平均健康分</text>
            </view>
            <view class="month-stat">
              <text class="value">{{ monthlyReport.record_rate }}%</text>
              <text class="label">记录率</text>
            </view>
          </view>
        </view>

        <view class="section">
          <text class="section-title">本月关系回顾</text>
          <text class="section-content">{{ monthlyReport.summary }}</text>
        </view>

        <view class="section">
          <text class="section-title">本月亮点时刻</text>
          <view class="highlight-list">
            <view 
              v-for="(item, index) in monthlyReport.highlights" 
              :key="index"
              class="highlight-item"
            >
              <text class="date">{{ item.date }}</text>
              <text class="content">{{ item.content }}</text>
            </view>
          </view>
        </view>

        <view class="section">
          <text class="section-title">成长与改善</text>
          <text class="section-content">{{ monthlyReport.growth }}</text>
        </view>
      </view>

      <view v-else class="empty">
        <text class="text">本月数据不足</text>
      </view>
    </view>

    <!-- 趋势 -->
    <view v-if="activeTab === 'trend'" class="report-content">
      <view class="trend-card">
        <text class="card-title">健康分趋势（近30天）</text>
        <view class="line-chart">
          <!-- 这里可以集成 uCharts 或其他图表库 -->
          <text class="placeholder">趋势图表</text>
        </view>
      </view>

      <view class="trend-card">
        <text class="card-title">情绪分布</text>
        <view class="emotion-stats">
          <view 
            v-for="emotion in emotionStats" 
            :key="emotion.name"
            class="emotion-bar"
          >
            <text class="emotion-name">{{ emotion.name }}</text>
            <view class="bar-container">
              <view 
                class="bar-fill"
                :style="{ width: emotion.percent + '%' }"
              ></view>
            </view>
            <text class="emotion-count">{{ emotion.count }}</text>
          </view>
        </view>
      </view>

      <view class="trend-card">
        <text class="card-title">互动频率</text>
        <view class="frequency-grid">
          <view 
            v-for="(day, index) in interactionGrid" 
            :key="index"
            :class="['grid-cell', getCellClass(day.count)]"
            :title="`${day.date}: ${day.count}次`"
          ></view>
        </view>
        <view class="legend">
          <text>少</text>
          <view class="legend-item level-0"></view>
          <view class="legend-item level-1"></view>
          <view class="legend-item level-2"></view>
          <view class="legend-item level-3"></view>
          <text>多</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeTab = ref('daily')
const tabs = [
  { key: 'daily', label: '日报' },
  { key: 'weekly', label: '周报' },
  { key: 'monthly', label: '月报' },
  { key: 'trend', label: '趋势' }
]

// 模拟数据
const dailyReport = ref({
  health_score: 85,
  summary: '今天你们进行了深度沟通，双方都表达了各自的想法。整体氛围积极，关系健康度保持良好。',
  observations: [
    '主动分享了工作中的困扰',
    '对方给予了积极回应',
    '共同规划了周末安排',
    '情绪表达真诚自然'
  ],
  suggestions: [
    '继续保持主动分享的习惯',
    '可以尝试一起做一件新鲜的事',
    '注意倾听对方的深层需求'
  ]
})

const weeklyReport = ref({
  daily_scores: [
    { label: '周一', score: 75 },
    { label: '周二', score: 80 },
    { label: '周三', score: 85 },
    { label: '周四', score: 78 },
    { label: '周五', score: 88 },
    { label: '周六', score: 92 },
    { label: '周日', score: 85 }
  ],
  summary: '本周关系整体稳定向好，互动质量有所提升。周末的深度交流效果尤其明显。',
  checkin_days: 7,
  interaction_count: 23,
  avg_feeling: 8.2,
  conflict_count: 1,
  suggestions: [
    '保持每天至少一次深度对话',
    '尝试共同完成一个小目标',
    '注意观察对方的情绪变化'
  ]
})

const monthlyReport = ref({
  avg_score: 82,
  record_rate: 87,
  summary: '本月关系稳定发展，双方在沟通方式上有明显进步。遇到分歧时能够更加理性地处理，互相理解的能力在增强。',
  highlights: [
    { date: '9月5日', content: '一起完成了周末郊游计划，关系升温' },
    { date: '9月12日', content: '成功化解了一次工作压力带来的情绪波动' },
    { date: '9月20日', content: '共同规划了未来三个月的目标' }
  ],
  growth: '本月最大的进步是学会了在冲突时先暂停冷静，而不是立即争论。双方都在努力理解对方的感受，这是关系成熟的重要标志。'
})

const emotionStats = ref([
  { name: '开心', count: 45, percent: 90 },
  { name: '平静', count: 38, percent: 76 },
  { name: '温暖', count: 32, percent: 64 },
  { name: '焦虑', count: 12, percent: 24 },
  { name: '失落', count: 8, percent: 16 }
])

const interactionGrid = ref(
  Array.from({ length: 90 }, (_, i) => ({
    date: `Day ${i + 1}`,
    count: Math.floor(Math.random() * 5)
  }))
)

const todayDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日`
})

const currentMonth = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}年${now.getMonth() + 1}月`
})

const getStatusText = (score) => {
  if (score >= 85) return '关系健康'
  if (score >= 70) return '整体良好'
  if (score >= 60) return '需要关注'
  return '建议改善'
}

const getCellClass = (count) => {
  if (count === 0) return 'level-0'
  if (count <= 1) return 'level-1'
  if (count <= 3) return 'level-2'
  return 'level-3'
}

const goCheckin = () => {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40rpx 30rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}

.title {
  font-size: 40rpx;
  font-weight: bold;
  color: #fff;
}

.tabs {
  display: flex;
  background: #fff;
  border-radius: 20rpx;
  padding: 10rpx;
  margin-bottom: 20rpx;
  overflow-x: auto;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  font-size: 26rpx;
  color: #666;
  border-radius: 15rpx;
  white-space: nowrap;
}

.tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: bold;
}

.report-content {
  margin-bottom: 20rpx;
}

.report-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
}

.score-section {
  display: flex;
  align-items: center;
  padding: 40rpx 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 30rpx;
}

.score-circle {
  width: 180rpx;
  height: 180rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-right: 30rpx;
}

.score-value {
  font-size: 56rpx;
  font-weight: bold;
  color: #fff;
}

.score-label {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

.score-desc {
  flex: 1;
}

.status {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 10rpx;
}

.date {
  font-size: 24rpx;
  color: #999;
}

.section {
  margin-bottom: 40rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 20rpx;
}

.section-content {
  font-size: 28rpx;
  line-height: 1.8;
  color: #666;
}

.observation-list {
  display: flex;
  flex-direction: column;
  gap: 15rpx;
}

.observation-item {
  display: flex;
  align-items: flex-start;
}

.bullet {
  font-size: 32rpx;
  color: #667eea;
  margin-right: 15rpx;
  line-height: 1.6;
}

.observation-item .text {
  flex: 1;
  font-size: 26rpx;
  line-height: 1.6;
  color: #666;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.action-item {
  display: flex;
  align-items: flex-start;
  padding: 20rpx;
  background: #f9f9f9;
  border-radius: 10rpx;
}

.number {
  width: 40rpx;
  height: 40rpx;
  background: #667eea;
  color: #fff;
  border-radius: 50%;
  text-align: center;
  line-height: 40rpx;
  font-size: 24rpx;
  margin-right: 20rpx;
}

.action-item .text {
  flex: 1;
  font-size: 26rpx;
  line-height: 1.8;
  color: #333;
}

/* 周报样式 */
.trend-section {
  padding: 30rpx 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 30rpx;
}

.trend-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 30rpx;
}

.trend-chart {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 250rpx;
  padding: 20rpx 0;
}

.chart-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bar {
  width: 60rpx;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 10rpx 10rpx 0 0;
  margin-bottom: 10rpx;
}

.bar-label {
  font-size: 20rpx;
  color: #999;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.stat-item {
  padding: 30rpx;
  background: #f9f9f9;
  border-radius: 15rpx;
  text-align: center;
}

.stat-value {
  font-size: 48rpx;
  font-weight: bold;
  color: #667eea;
  display: block;
  margin-bottom: 10rpx;
}

.stat-label {
  font-size: 24rpx;
  color: #999;
}

/* 月报样式 */
.month-header {
  padding: 30rpx 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 30rpx;
}

.month-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 30rpx;
}

.month-stats {
  display: flex;
  gap: 40rpx;
}

.month-stat {
  text-align: center;
}

.month-stat .value {
  font-size: 56rpx;
  font-weight: bold;
  color: #667eea;
  display: block;
  margin-bottom: 10rpx;
}

.month-stat .label {
  font-size: 24rpx;
  color: #999;
}

.highlight-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.highlight-item {
  padding: 25rpx;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-left: 4rpx solid #667eea;
  border-radius: 10rpx;
}

.highlight-item .date {
  font-size: 24rpx;
  color: #667eea;
  display: block;
  margin-bottom: 10rpx;
}

.highlight-item .content {
  font-size: 26rpx;
  line-height: 1.6;
  color: #333;
}

/* 趋势样式 */
.trend-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 30rpx;
}

.line-chart {
  height: 400rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9f9f9;
  border-radius: 10rpx;
}

.placeholder {
  font-size: 40rpx;
  color: #ccc;
}

.emotion-stats {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.emotion-bar {
  display: flex;
  align-items: center;
  gap: 15rpx;
}

.emotion-name {
  width: 100rpx;
  font-size: 26rpx;
  color: #333;
}

.bar-container {
  flex: 1;
  height: 30rpx;
  background: #f0f0f0;
  border-radius: 15rpx;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 15rpx;
}

.emotion-count {
  width: 60rpx;
  text-align: right;
  font-size: 24rpx;
  color: #999;
}

.frequency-grid {
  display: grid;
  grid-template-columns: repeat(15, 1fr);
  gap: 6rpx;
  margin-bottom: 20rpx;
}

.grid-cell {
  width: 100%;
  padding-bottom: 100%;
  border-radius: 4rpx;
}

.level-0 { background: #ebedf0; }
.level-1 { background: #c6e48b; }
.level-2 { background: #7bc96f; }
.level-3 { background: #239a3b; }

.legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10rpx;
  font-size: 20rpx;
  color: #999;
}

.legend-item {
  width: 20rpx;
  height: 20rpx;
  border-radius: 4rpx;
}

/* 空状态 */
.empty {
  background: #fff;
  border-radius: 20rpx;
  padding: 100rpx 30rpx;
  text-align: center;
}

.empty .text {
  font-size: 28rpx;
  color: #999;
  display: block;
  margin-bottom: 40rpx;
}
</style>

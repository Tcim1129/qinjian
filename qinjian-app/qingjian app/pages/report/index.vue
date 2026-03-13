<template>
  <view class="report-page">
    <view class="report-header">
      <text class="eyebrow">REPORT</text>
      <text class="title">关系报告与阶段回顾</text>
      <text class="subtitle">把每天的情绪、互动和深聊节奏沉淀成趋势与建议。</text>
    </view>

    <scroll-view class="report-scroll" scroll-y>
      <view class="tab-row">
        <text v-for="tab in tabs" :key="tab.key" class="tab-chip" :class="{ active: currentTab === tab.key }" @click="switchTab(tab.key)">{{ tab.label }}</text>
      </view>

      <view class="hero-card">
        <view class="score-block">
          <text class="score-number">{{ reportView.healthScore ?? '--' }}</text>
          <text class="score-unit">健康分</text>
        </view>
        <view class="hero-copy-block">
          <text class="hero-title">{{ reportView.title || '等待生成' }}</text>
          <text class="hero-copy">{{ reportView.insight || '完成打卡后，这里会出现更贴近你们关系节奏的核心洞察。' }}</text>
        </view>
      </view>

      <view class="panel-card" v-if="reportView.suggestion">
        <text class="panel-title">AI 专属建议</text>
        <text class="panel-copy">{{ reportView.suggestion }}</text>
      </view>

      <view class="double-grid">
        <view class="panel-card">
          <text class="panel-title">关系亮点</text>
          <view v-if="reportView.highlights.length" class="bullet-list">
            <text v-for="item in reportView.highlights" :key="item" class="bullet-item">{{ item }}</text>
          </view>
          <text v-else class="panel-copy">当前暂无高亮点展示。</text>
        </view>

        <view class="panel-card">
          <text class="panel-title">需要关注</text>
          <view v-if="reportView.concerns.length" class="bullet-list">
            <text v-for="item in reportView.concerns" :key="item" class="bullet-item">{{ item }}</text>
          </view>
          <text v-else class="panel-copy">当前暂无明显风险提示。</text>
        </view>
      </view>

      <view class="panel-card">
        <view class="panel-header">
          <text class="panel-title">历史报告</text>
          <button class="generate-btn" @click="generateCurrent">生成当前</button>
        </view>
        <view class="history-list">
          <view v-for="item in historyListView" :key="item.id" class="history-item" @click="viewReport(item)">
            <view>
              <text class="history-title">{{ item._label }}</text>
              <text class="history-meta">{{ item.created_at || item.report_date || '' }}</text>
            </view>
            <text class="history-arrow">›</text>
          </view>
          <text v-if="!historyListView.length" class="panel-copy">还没有历史报告。</text>
        </view>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>

    <FloatingTabBar current="/pages/report/index" />
  </view>
</template>

<script>
import api from '../../utils/api.js'
import { syncSession } from '../../utils/session.js'
import FloatingTabBar from '../../components/FloatingTabBar.vue'

export default {
  components: { FloatingTabBar },
  data() {
    return {
      tabs: [
        { key: 'daily', label: '日报' },
        { key: 'weekly', label: '周报' },
        { key: 'monthly', label: '月报' },
      ],
      currentTab: 'daily',
      historyListView: [],
      reportView: {
        title: '等待生成',
        healthScore: null,
        insight: '',
        suggestion: '',
        highlights: [],
        concerns: [],
      },
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      if (!api.isLoggedIn()) return
      try {
        await syncSession(this.$store)
      } catch (e) {
        console.warn('report sync failed', e)
      }
      await this.loadReports()
    },
    switchTab(tab) {
      this.currentTab = tab
      this.loadReports()
    },
    normalizeReport(report) {
      const content = report?.content || {}
      return {
        title: this.currentTab === 'weekly' ? '周报' : this.currentTab === 'monthly' ? '月报' : '日报',
        healthScore: content.health_score || content.overall_health_score || null,
        insight: content.insight || content.executive_summary || content.self_insight || '',
        suggestion: content.suggestion || content.self_care_tip || '',
        highlights: content.highlights || content.weekly_highlights || content.strengths || [],
        concerns: content.concerns || content.areas_to_improve || content.growth_areas || [],
      }
    },
    async loadReports() {
      const pairId = this.$store.state.pairInfo?.id
      if (!pairId) return
      try {
        const [latest, history] = await Promise.all([
          api.getLatestReport(pairId, this.currentTab).catch(() => null),
          api.getReportHistory(pairId, this.currentTab, 7).catch(() => []),
        ])
        this.reportView = this.normalizeReport(latest)
        this.historyListView = (history || []).map((item) => ({
          ...item,
          _label: item.type === 'weekly' ? '周报' : item.type === 'monthly' ? '月报' : '日报'
        }))
      } catch (e) {
        console.warn('load reports failed', e)
      }
    },
    viewReport(item) {
      this.reportView = this.normalizeReport(item)
    },
    async generateCurrent() {
      const pairId = this.$store.state.pairInfo?.id
      if (!pairId) {
        uni.showToast({ title: '先绑定关系再生成报告', icon: 'none' })
        return
      }
      try {
        if (this.currentTab === 'weekly') {
          await api.generateWeeklyReport(pairId)
        } else if (this.currentTab === 'monthly') {
          await api.generateMonthlyReport(pairId)
        } else {
          await api.generateDailyReport(pairId)
        }
        uni.showToast({ title: '已开始生成', icon: 'success' })
        setTimeout(() => this.loadReports(), 1600)
      } catch (e) {
        uni.showToast({ title: e.message || '生成失败', icon: 'none' })
      }
    }
  }
}
</script>

<style scoped>
.report-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff9f3 0%, #f5eee7 100%);
}

.report-header {
  padding: 84rpx 28rpx 28rpx;
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.title {
  display: block;
  margin-top: 18rpx;
  font-size: 48rpx;
  line-height: 1.2;
  font-weight: 800;
  color: #2f2522;
}

.subtitle {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.report-scroll {
  height: calc(100vh - 140rpx);
  padding: 0 28rpx;
  box-sizing: border-box;
}

.tab-row {
  display: flex;
  gap: 12rpx;
}

.tab-chip {
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: #f4ece3;
  color: #8d6e63;
  font-size: 22rpx;
  font-weight: 700;
}

.tab-chip.active {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.hero-card,
.panel-card {
  background: rgba(255,255,255,0.96);
  border-radius: 32rpx;
  box-shadow: 0 16rpx 32rpx rgba(62, 39, 35, 0.08);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.hero-card {
  margin-top: 24rpx;
  padding: 28rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.score-block {
  width: 180rpx;
  height: 180rpx;
  border-radius: 90rpx;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.score-number {
  font-size: 56rpx;
  font-weight: 900;
}

.score-unit {
  font-size: 20rpx;
  opacity: 0.82;
}

.hero-copy-block {
  flex: 1;
}

.hero-title,
.panel-title,
.history-title {
  font-size: 28rpx;
  font-weight: 800;
  color: #2f2522;
}

.hero-copy,
.panel-copy,
.history-meta {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.panel-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.double-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}

.bullet-list {
  margin-top: 14rpx;
}

.bullet-item {
  display: block;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f2e9df;
  font-size: 22rpx;
  line-height: 1.8;
  color: #3e2723;
}

.bullet-item:last-child {
  border-bottom: none;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.generate-btn {
  height: 68rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  border: none;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
}

.history-list {
  margin-top: 18rpx;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.history-item:last-child {
  border-bottom: none;
}

.history-arrow {
  font-size: 34rpx;
  color: #a1887f;
}

.page-spacer {
  height: 180rpx;
}
</style>

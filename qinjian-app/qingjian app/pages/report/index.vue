<template>
  <view class="report-page">
    <scroll-view class="report-scroll" scroll-y enable-back-to-top>
      <!-- Loading state -->
      <view class="loading-shell" v-if="loading && !reportView">
        <view class="loading-spinner"></view>
        <text class="loading-text">加载中...</text>
      </view>

      <!-- Empty state -->
      <view class="empty-shell" v-if="!loading && !reportView">
        <view class="empty-icon">📋</view>
        <text class="empty-title">暂无报告</text>
        <text class="empty-desc">完成今日打卡后，系统会自动生成关系报告</text>
        <button class="btn-primary" @click="goCheckin">去打卡</button>
      </view>

      <!-- Report content -->
      <view v-if="reportView" class="report-body">
        <!-- Score card -->
        <view class="score-card">
          <view class="score-card__top">
            <view class="score-card__brand">
              <text class="score-card__eyebrow">亲健</text>
              <text class="score-card__title">关系报告</text>
            </view>
            <text class="score-card__date">{{ reportContent && (reportContent.report_date || reportContent.created_at) || '' }}</text>
          </view>
          <view class="score-card__main">
            <text class="score-number">{{ reportView.healthScore !== null && reportView.healthScore !== undefined ? reportView.healthScore : '--' }}</text>
            <text class="score-unit">/ 100</text>
          </view>
          <text class="score-card__insight" v-if="reportView.insight">{{ reportView.insight }}</text>
          <view class="score-card__suggestion" v-if="reportView.suggestion">
            <text class="suggestion-label">下一步建议</text>
            <text class="suggestion-text">{{ reportView.suggestion }}</text>
          </view>
        </view>

        <!-- Tabs -->
        <view class="segment-tabs">
          <text
            v-for="tab in tabs"
            :key="tab.key"
            class="segment-tabs__item"
            :class="{ active: currentTab === tab.key }"
            @click="switchTab(tab.key)"
          >{{ tab.label }}</text>
        </view>

        <!-- Highlights & Concerns -->
        <view class="content-grid" v-if="(reportView.highlights && reportView.highlights.length) || (reportView.concerns && reportView.concerns.length)">
          <view class="content-card" v-if="reportView.highlights && reportView.highlights.length">
            <text class="content-card__title">关系亮点</text>
            <view class="bullet-list">
              <text v-for="item in reportView.highlights" :key="item" class="bullet-item">{{ item }}</text>
            </view>
          </view>
          <view class="content-card content-card--warn" v-if="reportView.concerns && reportView.concerns.length">
            <text class="content-card__title">关注点</text>
            <view class="bullet-list">
              <text v-for="item in reportView.concerns" :key="item" class="bullet-item">{{ item }}</text>
            </view>
          </view>
        </view>

        <!-- Safety boundary -->
        <view class="content-card content-card--border" v-if="safetyStatus">
          <text class="content-card__title">安全边界</text>
          <view class="safety-row">
            <text class="safety-pill">{{ safetyStatus.risk_level || 'low' }}</text>
            <text class="safety-why">{{ safetyStatus.why_now }}</text>
          </view>
          <view class="evidence-list" v-if="safetyStatus.evidence_summary && safetyStatus.evidence_summary.length">
            <text v-for="item in safetyStatus.evidence_summary" :key="item" class="evidence-chip">{{ item }}</text>
          </view>
          <text class="content-card__note" v-if="reportView.limitationNote || safetyStatus.limitation_note">
            {{ reportView.limitationNote || safetyStatus.limitation_note }}
          </text>
          <text class="content-card__alert" v-if="reportView.safetyHandoff || safetyStatus.handoff_recommendation">
            {{ reportView.safetyHandoff || safetyStatus.handoff_recommendation }}
          </text>
        </view>

        <!-- Assessment trend -->
        <view class="content-card" v-if="assessmentTrend">
          <text class="content-card__title">近 4 次体检趋势</text>
          <view class="trend-head">
            <text class="trend-score">{{ assessmentTrend.latestScore !== null && assessmentTrend.latestScore !== undefined ? assessmentTrend.latestScore : '--' }}</text>
            <text class="trend-desc">{{ assessmentTrend.changeSummary }}</text>
          </view>
          <view class="trend-points" v-if="assessmentTrend.points && assessmentTrend.points.length">
            <view class="trend-point" v-for="item in assessmentTrend.points" :key="item.id">
              <text class="trend-point__label">{{ item.label }}</text>
              <text class="trend-point__score">{{ item.score }}</text>
              <text class="trend-point__summary">{{ item.summary }}</text>
            </view>
          </view>
          <view class="dimension-grid" v-if="assessmentTrend.dimensions && assessmentTrend.dimensions.length">
            <view class="dimension-item" v-for="item in assessmentTrend.dimensions" :key="item.id">
              <text class="dimension-item__label">{{ item.label }}</text>
              <text class="dimension-item__score">{{ item.score !== null && item.score !== undefined ? item.score : '--' }}</text>
              <view class="dimension-meter">
                <view class="dimension-meter__fill" :style="{ width: `${item.score || 0}%` }"></view>
              </view>
            </view>
          </view>
        </view>

        <!-- History -->
        <view class="history-section">
          <text class="history-section__title">历史报告</text>
          <view class="history-list" v-if="historyListView && historyListView.length">
            <view
              class="history-item"
              v-for="item in historyListView"
              :key="item.id"
              @click="viewReport(item)"
            >
              <view class="history-item__info">
                <text class="history-item__title">{{ item._label || '报告' }}</text>
                <text class="history-item__date">{{ item.created_at || item.report_date || '' }}</text>
              </view>
              <text class="history-item__arrow">›</text>
            </view>
          </view>
          <text class="history-section__empty" v-else>暂无历史报告</text>
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

function normalizeAssessmentTrend(payload) {
  if (!payload) return null
  return {
    latestScore: payload.latest_score,
    changeSummary: payload.change_summary,
    points: (payload.trend_points || []).slice(-4).map((item) => ({
      id: item.event_id,
      label: (item.submitted_at || '').slice(5, 10) || '本周',
      score: item.total_score,
      summary: item.change_summary || '系统已记录本次评估'
    })),
    dimensions: (payload.dimension_scores || []).slice(0, 5).map((item) => ({
      id: item.id,
      label: item.label,
      score: item.score
    }))
  }
}

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
      reportView: null,
      reportContent: null,
      historyListView: [],
      safetyStatus: null,
      assessmentTrend: null,
      policyAudit: null,
      loading: false
    }
  },
  computed: {
    pairId() {
      return this.$store.state.pairInfo?.id || null
    },
    isSolo() {
      return !this.pairId
    },
    currentReportLabel() {
      if (this.currentTab === 'weekly') return '周报'
      if (this.currentTab === 'monthly') return '月报'
      return this.isSolo ? '个人日报' : '日报'
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
      } catch (error) {
        console.warn('report sync failed', error)
      }
      await this.loadDashboard()
    },
    switchTab(tab) {
      this.currentTab = tab
      this.loadDashboard()
    },
    normalizeReport(report) {
      if (!report) return null
      const content = report.content || {}
      const type = report.type || this.currentTab
      return {
        title: type === 'solo' ? '个人日报' : type === 'weekly' ? '周报' : type === 'monthly' ? '月报' : '日报',
        healthScore: content.health_score || content.overall_health_score || null,
        insight: content.insight || content.self_insight || content.executive_summary || '',
        suggestion: content.suggestion || content.self_care_tip || content.professional_note || '',
        highlights: content.highlights || content.weekly_highlights || content.strengths || [],
        concerns: content.concerns || content.areas_to_improve || content.growth_areas || [],
        evidenceSummary: report.evidence_summary || [],
        limitationNote: report.limitation_note || '',
        safetyHandoff: report.safety_handoff || ''
      }
    },
    async loadDashboard() {
      this.loading = true
      const pairId = this.pairId
      try {
        const latestRequest = !pairId && this.currentTab !== 'daily'
          ? Promise.resolve(null)
          : api.getLatestReport(pairId, this.currentTab).catch(() => null)
        const historyRequest = !pairId && this.currentTab !== 'daily'
          ? Promise.resolve([])
          : api.getReportHistory(pairId, this.currentTab, 6).catch(() => [])

        const [latest, history, safetyStatus, assessmentTrend, policyAudit] = await Promise.all([
          latestRequest,
          historyRequest,
          api.getSafetyStatus(pairId).catch(() => null),
          api.getWeeklyAssessmentTrend(pairId).catch(() => null),
          api.getPolicyDecisionAudit(pairId).catch(() => null)
        ])
        this.reportContent = latest
        this.reportView = this.normalizeReport(latest)
        this.historyListView = (history || []).map((item) => ({
          ...item,
          _label: item.type === 'solo' ? '个人日报' : item.type === 'weekly' ? '周报' : item.type === 'monthly' ? '月报' : '日报'
        }))
        this.safetyStatus = safetyStatus
        this.assessmentTrend = normalizeAssessmentTrend(assessmentTrend)
        this.policyAudit = policyAudit
      } catch (error) {
        console.warn('load report dashboard failed', error)
      } finally {
        this.loading = false
      }
    },
    viewReport(item) {
      this.reportContent = item
      this.reportView = this.normalizeReport(item)
    },
    goCheckin() {
      uni.navigateTo({ url: '/pages/checkin/index' })
    }
  }
}
</script>

<style scoped>
.report-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #fff9f3 0%, #f4ede6 100%);
}

.report-scroll {
  flex: 1;
  min-height: 0;
  padding: 24rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

/* Loading & Empty */
.loading-shell,
.empty-shell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 40rpx;
  text-align: center;
}

.loading-spinner {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid rgba(212, 163, 115, 0.2);
  border-top-color: #8d6e63;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 20rpx;
  font-size: 24rpx;
  color: #a1887f;
}

.empty-icon {
  font-size: 96rpx;
  margin-bottom: 24rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 800;
  color: #2f2522;
  margin-bottom: 12rpx;
}

.empty-desc {
  font-size: 24rpx;
  color: #8d6e63;
  line-height: 1.6;
  margin-bottom: 40rpx;
}

.btn-primary {
  width: 100%;
  height: 88rpx;
  border-radius: 44rpx;
  border: none;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  font-size: 28rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Report body */
.report-body {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

/* Score card */
.score-card {
  border-radius: 36rpx;
  padding: 36rpx 32rpx;
  background: linear-gradient(145deg, rgba(255, 247, 240, 0.98), rgba(240, 248, 252, 0.92));
  border: 1rpx solid rgba(212, 163, 115, 0.14);
  box-shadow: 0 20rpx 44rpx rgba(93, 64, 55, 0.08);
}

.score-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.score-card__brand {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.score-card__eyebrow {
  font-size: 18rpx;
  letter-spacing: 4rpx;
  color: #a1887f;
}

.score-card__title {
  font-size: 28rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
}

.score-card__date {
  font-size: 20rpx;
  color: #a1887f;
}

.score-card__main {
  display: flex;
  align-items: flex-end;
  gap: 8rpx;
  margin-top: 28rpx;
}

.score-number {
  font-size: 72rpx;
  font-weight: 900;
  line-height: 1;
  color: #5B8DEE;
}

.score-unit {
  font-size: 24rpx;
  color: #8d6e63;
  padding-bottom: 8rpx;
}

.score-card__insight {
  display: block;
  margin-top: 20rpx;
  font-size: 26rpx;
  line-height: 1.7;
  color: #3e2723;
  font-weight: 600;
}

.score-card__suggestion {
  margin-top: 16rpx;
  padding: 20rpx;
  border-radius: 20rpx;
  background: rgba(255, 247, 225, 0.95);
}

.suggestion-label {
  display: block;
  font-size: 18rpx;
  letter-spacing: 2rpx;
  color: #a1887f;
  margin-bottom: 6rpx;
}

.suggestion-text {
  display: block;
  font-size: 24rpx;
  line-height: 1.7;
  color: #3e2723;
}

/* Segment tabs */
.segment-tabs {
  display: flex;
  padding: 6rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.9);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.segment-tabs__item {
  flex: 1;
  padding: 16rpx 0;
  text-align: center;
  font-size: 24rpx;
  font-weight: 700;
  color: #8d6e63;
  border-radius: 18rpx;
  transition: all 0.2s ease;
}

.segment-tabs__item.active {
  color: #fff;
  background: linear-gradient(135deg, #5B8DEE, #8BAFF2);
  box-shadow: 0 6rpx 16rpx rgba(91, 141, 238, 0.18);
}

/* Content cards */
.content-card {
  border-radius: 28rpx;
  padding: 28rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 12rpx 28rpx rgba(62, 39, 35, 0.06);
}

.content-card--warn {
  border-color: rgba(255, 152, 0, 0.2);
}

.content-card--border {
  border-color: rgba(212, 163, 115, 0.18);
}

.content-card__title {
  font-size: 26rpx;
  font-weight: 800;
  color: #2f2522;
  margin-bottom: 16rpx;
  display: block;
}

.content-card__note {
  display: block;
  margin-top: 16rpx;
  padding: 16rpx;
  border-radius: 16rpx;
  background: #f8f1eb;
  font-size: 22rpx;
  line-height: 1.7;
  color: #6d4c41;
}

.content-card__alert {
  display: block;
  margin-top: 16rpx;
  padding: 16rpx;
  border-radius: 16rpx;
  background: rgba(255, 236, 229, 0.92);
  color: #8a3b2f;
  font-size: 22rpx;
  line-height: 1.7;
}

/* Content grid */
.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}

/* Bullet list */
.bullet-list {
  display: flex;
  flex-direction: column;
}

.bullet-item {
  display: block;
  padding: 12rpx 0;
  font-size: 22rpx;
  line-height: 1.7;
  color: #3e2723;
  border-bottom: 1rpx solid #f2e9df;
}

.bullet-item:last-child {
  border-bottom: none;
}

/* Safety */
.safety-row {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.safety-pill {
  align-self: flex-start;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 244, 231, 0.94);
  color: #8d5b3e;
  font-size: 18rpx;
  font-weight: 700;
}

.safety-why {
  font-size: 22rpx;
  line-height: 1.7;
  color: #3e2723;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.evidence-chip {
  padding: 10rpx 14rpx;
  border-radius: 16rpx;
  background: #fcf4ed;
  font-size: 20rpx;
  color: #6d4c41;
}

/* Trend */
.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 12rpx;
}

.trend-score {
  font-size: 48rpx;
  font-weight: 900;
  color: #5B8DEE;
  line-height: 1;
}

.trend-desc {
  font-size: 22rpx;
  color: #6d4c41;
  text-align: right;
}

.trend-points {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14rpx;
  margin-top: 18rpx;
}

.trend-point {
  padding: 18rpx;
  border-radius: 18rpx;
  background: #fcf4ed;
}

.trend-point__label {
  font-size: 18rpx;
  color: #a1887f;
}

.trend-point__score {
  font-size: 28rpx;
  font-weight: 800;
  color: #3e2723;
  margin-top: 6rpx;
  display: block;
}

.trend-point__summary {
  font-size: 18rpx;
  color: #8d6e63;
  margin-top: 6rpx;
  line-height: 1.5;
  display: block;
}

/* Dimension grid */
.dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14rpx;
  margin-top: 18rpx;
}

.dimension-item {
  padding: 18rpx;
  border-radius: 18rpx;
  background: #f8f1eb;
}

.dimension-item__label {
  font-size: 18rpx;
  color: #a1887f;
}

.dimension-item__score {
  font-size: 28rpx;
  font-weight: 800;
  color: #3e2723;
  margin-top: 6rpx;
  display: block;
}

.dimension-meter {
  height: 8rpx;
  margin-top: 12rpx;
  border-radius: 999rpx;
  background: rgba(212, 163, 115, 0.16);
  overflow: hidden;
}

.dimension-meter__fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #5B8DEE, #8BAFF2);
}

/* History */
.history-section {
  margin-top: 8rpx;
}

.history-section__title {
  font-size: 26rpx;
  font-weight: 800;
  color: #2f2522;
  margin-bottom: 16rpx;
  display: block;
}

.history-section__empty {
  font-size: 22rpx;
  color: #a1887f;
  text-align: center;
  padding: 32rpx 0;
  display: block;
}

.history-list {
  display: flex;
  flex-direction: column;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.history-item:last-child {
  border-bottom: none;
}

.history-item__info {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.history-item__title {
  font-size: 24rpx;
  font-weight: 700;
  color: #3e2723;
}

.history-item__date {
  font-size: 20rpx;
  color: #a1887f;
}

.history-item__arrow {
  font-size: 28rpx;
  color: #b08b73;
}

.page-spacer {
  height: 120rpx;
}

@media (max-width: 390px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .trend-points,
  .dimension-grid {
    grid-template-columns: 1fr;
  }
}
</style>

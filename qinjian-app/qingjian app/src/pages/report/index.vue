<template>
  <view class="report-page">
    <scroll-view class="report-scroll" scroll-y>
      <view class="hero-shell">
        <view class="brand-chip">
          <image class="brand-chip__logo" src="../../static/brand-logo.jpg" mode="aspectFit"></image>
          <view class="brand-chip__copy">
            <text class="brand-chip__eyebrow">QINJIAN APP</text>
            <text class="brand-chip__name">关系报告</text>
          </view>
        </view>
        <text class="hero-title">把简报、边界、体检趋势和策略摘要收进同一张作品级面板</text>
        <view class="section-rule"></view>
        <text class="hero-subtitle">这页不只给你一句建议，还会解释系统为什么这么判断、现在该推进还是减压，以及哪一条证据在影响下一步。</text>

        <view class="hero-toolbar">
          <view class="tab-row">
            <text
              v-for="tab in tabs"
              :key="tab.key"
              class="tab-chip"
              :class="{ active: currentTab === tab.key }"
              @click="switchTab(tab.key)"
            >{{ tab.label }}</text>
          </view>
          <button class="generate-btn" @click="generateCurrent" :disabled="generating">
            {{ generating ? '正在生成...' : generateLabel }}
          </button>
        </view>
      </view>

      <view v-if="reportView" class="cockpit-card hero-card">
        <view class="hero-score">
          <text class="hero-score__value">{{ reportView.healthScore !== null && reportView.healthScore !== undefined ? reportView.healthScore : '--' }}</text>
          <text class="hero-score__unit">/ 100</text>
        </view>
        <view class="hero-copy">
          <text class="section-eyebrow">HERO</text>
          <text class="card-title">{{ reportView.title || currentReportLabel }}</text>
          <text class="hero-insight">{{ reportView.insight || emptyHint }}</text>
          <view class="hero-chip-row">
            <text class="hero-chip">{{ isSolo ? 'SOLO MODE' : 'PAIR MODE' }}</text>
            <text v-if="reportView.evidenceSummary.length" class="hero-chip hero-chip--soft">有可解释证据</text>
            <text v-if="reportView.safetyHandoff" class="hero-chip hero-chip--alert">需要人工支持边界</text>
          </view>
          <view v-if="reportView.suggestion" class="hero-focus-box">
            <text class="focus-label">下一步动作</text>
            <text class="focus-copy">{{ reportView.suggestion }}</text>
          </view>
        </view>
      </view>
      <view v-else class="cockpit-card empty-card">
        <text class="section-eyebrow">HERO</text>
        <text class="card-title">{{ currentReportLabel }}</text>
        <text class="empty-copy">{{ emptyHint }}</text>
      </view>

      <view v-if="safetyStatus" class="cockpit-card">
        <text class="section-eyebrow">TRUST & BOUNDARY</text>
        <text class="card-title">这次判断的边界与依据</text>
        <view class="risk-row">
          <text class="risk-pill">{{ safetyStatus.risk_level || 'low' }}</text>
          <text class="risk-copy">{{ safetyStatus.why_now }}</text>
        </view>
        <view v-if="safetyStatus.evidence_summary && safetyStatus.evidence_summary.length" class="evidence-chip-list">
          <text v-for="item in safetyStatus.evidence_summary" :key="item" class="evidence-chip">{{ item }}</text>
        </view>
        <text class="panel-copy">{{ reportView && reportView.limitationNote ? reportView.limitationNote : safetyStatus.limitation_note }}</text>
        <view v-if="(reportView && reportView.safetyHandoff) || safetyStatus.handoff_recommendation" class="handoff-box">
          {{ reportView && reportView.safetyHandoff ? reportView.safetyHandoff : safetyStatus.handoff_recommendation }}
        </view>
      </view>

      <view v-if="assessmentTrend" class="cockpit-card">
        <text class="section-eyebrow">ASSESSMENT</text>
        <text class="card-title">近 4 次正式关系体检</text>
        <view class="assessment-headline">
          <view>
            <text class="metric-label">最新总分</text>
            <text class="metric-value">{{ assessmentTrend.latestScore !== null && assessmentTrend.latestScore !== undefined ? assessmentTrend.latestScore : '--' }}</text>
          </view>
          <text class="metric-copy">{{ assessmentTrend.changeSummary }}</text>
        </view>
        <view v-if="assessmentTrend.points.length" class="mini-grid two-column">
          <view v-for="item in assessmentTrend.points" :key="item.id" class="mini-card">
            <text class="mini-label">{{ item.label }}</text>
            <text class="mini-value">{{ item.score }}</text>
            <text class="mini-copy">{{ item.summary }}</text>
          </view>
        </view>
        <view v-if="assessmentTrend.dimensions.length" class="mini-grid three-column">
          <view v-for="item in assessmentTrend.dimensions" :key="item.id" class="mini-card mini-card--plain">
            <text class="mini-label">{{ item.label }}</text>
            <text class="mini-value">{{ item.score !== null && item.score !== undefined ? item.score : '--' }}</text>
            <view class="mini-meter">
              <view class="mini-meter__fill" :style="{ width: `${item.score || 0}%` }"></view>
            </view>
          </view>
        </view>
      </view>

      <view class="evidence-grid">
        <view class="cockpit-card">
          <text class="section-eyebrow">EVIDENCE</text>
          <text class="card-title">这段关系现在的亮点</text>
          <view v-if="reportView && reportView.highlights && reportView.highlights.length" class="bullet-list">
            <text v-for="item in reportView.highlights" :key="item" class="bullet-item">{{ item }}</text>
          </view>
          <text v-else class="empty-copy">系统还在等待更多稳定正向信号。</text>
        </view>

        <view class="cockpit-card">
          <text class="section-eyebrow">WATCH</text>
          <text class="card-title">需要继续盯住的点</text>
          <view v-if="reportView && reportView.concerns && reportView.concerns.length" class="bullet-list">
            <text v-for="item in reportView.concerns" :key="item" class="bullet-item">{{ item }}</text>
          </view>
          <text v-else class="empty-copy">当前没有明显升级风险，继续稳住节奏就好。</text>
        </view>
      </view>

      <view v-if="policyAudit" class="cockpit-card">
        <text class="section-eyebrow">POLICY</text>
        <text class="card-title">系统当前的策略判断</text>
        <view class="mini-grid two-column">
          <view class="mini-card">
            <text class="mini-label">当前策略</text>
            <text class="mini-value mini-value--title">{{ policyAudit.current_policy ? policyAudit.current_policy.title : '继续观察' }}</text>
          </view>
          <view class="mini-card">
            <text class="mini-label">推荐下一步</text>
            <text class="mini-value mini-value--title">{{ policyAudit.recommended_policy ? policyAudit.recommended_policy.title : '先保持当前版本' }}</text>
          </view>
        </view>
        <text class="panel-copy">{{ policyAudit.selection_reason || policyAudit.schedule_summary || '系统会持续把打卡、体检和任务反馈回流到下一个决策点。' }}</text>
      </view>

      <view class="cockpit-card">
        <view class="section-head">
          <view>
            <text class="section-eyebrow">HISTORY</text>
            <text class="card-title">历史简报</text>
          </view>
        </view>
        <view v-if="historyListView.length" class="history-list">
          <view v-for="item in historyListView" :key="item.id" class="history-item" @click="viewReport(item)">
            <view>
              <text class="history-title">{{ item._label }}</text>
              <text class="history-meta">{{ item.created_at || item.report_date || '' }}</text>
            </view>
            <text class="history-arrow">→</text>
          </view>
        </view>
        <text v-else class="empty-copy">还没有可回看的历史简报。</text>
      </view>

      <view class="cockpit-card action-card">
        <text class="section-eyebrow">ACTION</text>
        <text class="card-title">继续推进这段关系的入口</text>
        <view class="action-grid">
          <view v-for="item in actions" :key="item.id" class="action-chip" @click="openAction(item)">
            <text class="action-name">{{ item.title }}</text>
            <text class="action-copy">{{ item.subtitle }}</text>
          </view>
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

const ACTIONS = [
  { id: 'assessment', title: '关系体检', subtitle: '正式提交本周评估', path: '/pages/discover/health-test/index', mode: 'navigate' },
  { id: 'profile', title: '我的空间', subtitle: '查看关系边界与设置', path: '/pages/profile/index', mode: 'reLaunch' },
  { id: 'discover', title: '发现页', subtitle: '回到工具与功能入口', path: '/pages/discover/index', mode: 'reLaunch' },
]

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
      actions: ACTIONS,
      currentTab: 'daily',
      reportView: null,
      reportContent: null,
      historyListView: [],
      safetyStatus: null,
      assessmentTrend: null,
      policyAudit: null,
      generating: false,
      emptyHint: '完成今天的记录后，这里会生成更像正式产品页面的关系简报。'
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
    },
    generateLabel() {
      if (this.currentTab === 'weekly') return '生成周报'
      if (this.currentTab === 'monthly') return '生成月报'
      return this.isSolo ? '生成个人日报' : '生成日报'
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
        this.emptyHint = !pairId && this.currentTab !== 'daily'
          ? '单人模式下，先从个人日报与每周体检开始积累连续证据。'
          : this.isSolo
          ? '先留下今天的个人记录，系统才会开始拼出更稳定的情绪和节奏趋势。'
          : '补上最近的打卡或体检后，系统会更稳地判断这段关系该推进还是减压。'
      } catch (error) {
        console.warn('load report dashboard failed', error)
      }
    },
    viewReport(item) {
      this.reportContent = item
      this.reportView = this.normalizeReport(item)
    },
    async generateCurrent() {
      if (this.generating) return
      const pairId = this.pairId
      if (!pairId && this.currentTab !== 'daily') {
        uni.showToast({ title: '单人模式下先从日报开始', icon: 'none' })
        return
      }
      try {
        this.generating = true
        if (this.currentTab === 'weekly') {
          await api.generateWeeklyReport(pairId)
        } else if (this.currentTab === 'monthly') {
          await api.generateMonthlyReport(pairId)
        } else {
          await api.generateDailyReport(pairId)
        }
        uni.showToast({ title: '已经开始生成', icon: 'success' })
        setTimeout(() => this.loadDashboard(), 1600)
      } catch (error) {
        uni.showToast({ title: error.message || '生成失败', icon: 'none' })
      } finally {
        this.generating = false
      }
    },
    openAction(action) {
      if (!action?.path) return
      if (action.mode === 'reLaunch') {
        uni.reLaunch({ url: action.path })
        return
      }
      uni.navigateTo({ url: action.path })
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
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.hero-shell,
.cockpit-card {
  border-radius: 34rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.hero-shell {
  padding: 32rpx;
  background: linear-gradient(145deg, rgba(255, 248, 241, 0.98), rgba(239, 247, 252, 0.92));
  position: relative;
  overflow: hidden;
  animation: cockpitFloat 7.6s ease-in-out infinite;
}

.hero-shell::after {
  content: "";
  position: absolute;
  right: -80rpx;
  top: -80rpx;
  width: 240rpx;
  height: 240rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212, 163, 115, 0.24), rgba(212, 163, 115, 0));
}

.brand-chip {
  display: inline-flex;
  align-items: center;
  gap: 14rpx;
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.82);
  border: 1rpx solid rgba(212, 163, 115, 0.14);
}

.brand-chip__logo {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
}

.brand-chip__copy {
  display: flex;
  flex-direction: column;
  gap: 2rpx;
}

.brand-chip__eyebrow,
.section-eyebrow,
.metric-label,
.focus-label {
  font-size: 18rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.brand-chip__name,
.card-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.4rpx;
}

.hero-title {
  display: block;
  margin-top: 22rpx;
  font-size: 40rpx;
  line-height: 1.42;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.6rpx;
}

.section-rule {
  width: 96rpx;
  height: 6rpx;
  margin-top: 16rpx;
  border-radius: 999rpx;
  background: linear-gradient(90deg, rgba(212, 163, 115, 0.92), rgba(93, 64, 55, 0.88));
}

.hero-subtitle,
.hero-insight,
.panel-copy,
.metric-copy,
.mini-copy,
.empty-copy,
.action-copy,
.history-meta,
.risk-copy,
.focus-copy {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.hero-toolbar {
  margin-top: 24rpx;
  display: grid;
  gap: 18rpx;
}

.tab-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
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

.generate-btn {
  height: 78rpx;
  border-radius: 999rpx;
  border: none;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  font-size: 24rpx;
  font-weight: 800;
}

.cockpit-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.hero-card {
  display: flex;
  gap: 24rpx;
  align-items: stretch;
}

.hero-score {
  width: 190rpx;
  border-radius: 30rpx;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #fff;
  box-shadow: 0 14rpx 28rpx rgba(93, 64, 55, 0.16);
}

.hero-score__value {
  font-size: 60rpx;
  font-weight: 900;
  line-height: 1;
}

.hero-score__unit {
  margin-top: 12rpx;
  font-size: 22rpx;
  opacity: 0.84;
}

.hero-copy {
  flex: 1;
}

.hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 18rpx;
}

.hero-chip {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #f8efe6;
  color: #8d6e63;
  font-size: 20rpx;
  font-weight: 700;
}

.hero-chip--soft {
  background: #eef4ef;
  color: #5f7463;
}

.hero-chip--alert {
  background: #fff0ea;
  color: #9d4d3f;
}

.hero-focus-box,
.handoff-box,
.mini-card,
.action-chip {
  border-radius: 24rpx;
}

.hero-focus-box {
  margin-top: 18rpx;
  padding: 20rpx 22rpx;
  background: linear-gradient(145deg, rgba(255, 247, 225, 0.98), rgba(255, 241, 214, 0.95));
}

.risk-row {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  margin-top: 18rpx;
}

.risk-pill {
  align-self: flex-start;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 244, 231, 0.94);
  color: #8d5b3e;
  font-size: 20rpx;
  font-weight: 700;
  text-transform: uppercase;
}

.evidence-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.evidence-chip {
  padding: 14rpx 18rpx;
  border-radius: 22rpx;
  background: #fcf4ed;
  color: #6d4c41;
  font-size: 22rpx;
  line-height: 1.6;
}

.handoff-box {
  margin-top: 18rpx;
  padding: 22rpx;
  background: rgba(255, 236, 229, 0.92);
  color: #8a3b2f;
  font-size: 22rpx;
  line-height: 1.8;
}

.assessment-headline {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  align-items: flex-end;
  margin-top: 16rpx;
}

.metric-value {
  display: block;
  margin-top: 8rpx;
  font-size: 54rpx;
  font-weight: 900;
  line-height: 1;
  color: #5d4037;
}

.mini-grid {
  display: grid;
  gap: 16rpx;
  margin-top: 22rpx;
}

.two-column {
  grid-template-columns: repeat(2, 1fr);
}

.three-column {
  grid-template-columns: repeat(3, 1fr);
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 24rpx;
}

.mini-card,
.action-chip {
  padding: 22rpx;
  background: #fcf4ed;
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 12rpx 24rpx rgba(93, 64, 55, 0.06);
}

.mini-card--plain {
  background: #f8f1eb;
}

.mini-label {
  font-size: 20rpx;
  color: #a1887f;
}

.mini-value {
  display: block;
  margin-top: 12rpx;
  font-size: 34rpx;
  font-weight: 900;
  color: #3e2723;
}

.mini-meter {
  height: 10rpx;
  margin-top: 14rpx;
  border-radius: 999rpx;
  background: rgba(212, 163, 115, 0.16);
  overflow: hidden;
}

.mini-meter__fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #5d4037, #d4a373);
}

.mini-value--title {
  font-size: 26rpx;
  line-height: 1.45;
}

.bullet-list {
  margin-top: 18rpx;
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

.history-list {
  margin-top: 16rpx;
}

.history-item {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  align-items: center;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.history-item:last-child {
  border-bottom: none;
}

.history-title,
.action-name {
  font-size: 26rpx;
  font-weight: 800;
  color: #3e2723;
}

.action-chip {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 164rpx;
  background: linear-gradient(145deg, rgba(255, 249, 242, 0.98), rgba(248, 241, 234, 0.96));
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.action-chip:active {
  transform: scale(0.985) translateY(2rpx);
  box-shadow: 0 6rpx 14rpx rgba(93, 64, 55, 0.08);
}

.history-arrow {
  font-size: 30rpx;
  color: #a1887f;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.action-card {
  margin-top: 24rpx;
}

.page-spacer {
  height: 120rpx;
}

@keyframes cockpitFloat {
  0%,
  100% {
    transform: translateY(0);
    box-shadow: 0 20rpx 44rpx rgba(62, 39, 35, 0.08);
  }
  50% {
    transform: translateY(-4rpx);
    box-shadow: 0 26rpx 56rpx rgba(62, 39, 35, 0.12);
  }
}

@media (max-width: 390px) {
  .hero-card {
    flex-direction: column;
  }

  .hero-score {
    width: 100%;
    min-height: 164rpx;
  }

  .three-column,
  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .evidence-grid {
    grid-template-columns: 1fr;
  }
}
</style>

const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    currentTab: 'daily',
    tabs: [
      { key: 'daily', label: '日报' },
      { key: 'weekly', label: '周报' },
      { key: 'monthly', label: '月报' }
    ],
    reportContent: null,
    reportView: null,
    historyList: [],
    historyListView: [],
    trendData: null,
    safetyStatus: null,
    assessmentTrend: null,
    policyAudit: null,
    loading: false
  },

  onShow() {
    if (!auth.checkLogin()) return
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
    this.loadDashboard()
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      currentTab: tab,
      reportContent: null,
      reportView: null
    })
    this.loadDashboard()
  },

  onPullDownRefresh() {
    this.loadDashboard().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  goCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  async loadDashboard() {
    this.setData({ loading: true })
    try {
      const pairId = auth.getPairId()
      const reportType = this.data.currentTab
      const [latest, history, trend, safetyStatus, assessmentTrend, policyAudit] = await Promise.all([
        pairId
          ? api.get(`/reports/latest?pair_id=${pairId}&report_type=${reportType}`).catch(() => null)
          : api.get(`/reports/latest?mode=solo&report_type=${reportType}`).catch(() => null),
        pairId
          ? api.get(`/reports/history?pair_id=${pairId}&report_type=${reportType}`).catch(() => [])
          : api.get(`/reports/history?mode=solo&report_type=${reportType}`).catch(() => []),
        pairId
          ? api.get('/reports/trend?pair_id=' + pairId).catch(() => null)
          : api.get('/reports/trend?mode=solo').catch(() => null),
        api.getSafetyStatus(pairId).catch(() => null),
        api.getWeeklyAssessmentTrend(pairId).catch(() => null),
        api.getPolicyDecisionAudit(pairId).catch(() => null)
      ])

      const list = history || []
      this.setData({
        reportContent: latest,
        reportView: this.normalizeReport(latest),
        historyList: list,
        historyListView: list.map(item => ({
          ...item,
          _label: item.type === 'solo' ? '个人日报' : item.type === 'weekly' ? '周报' : item.type === 'monthly' ? '月报' : '日报'
        })),
        trendData: trend,
        safetyStatus,
        assessmentTrend: this.normalizeAssessmentTrend(assessmentTrend),
        policyAudit
      })
    } catch (e) {
      console.error('加载报告失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  viewReport(e) {
    const report = e.currentTarget.dataset.report
    this.setData({ reportContent: report, reportView: this.normalizeReport(report) })
  },

  normalizeReport(report) {
    if (!report) return null
    const content = report.content || {}
    const type = report.type || this.data.currentTab
    return {
      title: type === 'solo' ? '个人日报' : type === 'weekly' ? '周报' : type === 'monthly' ? '月报' : '日报',
      healthScore: content.health_score || content.overall_health_score || null,
      insight: content.insight || content.self_insight || content.executive_summary || '',
      suggestion: content.suggestion || content.self_care_tip || content.professional_note || '',
      highlights: content.highlights || content.weekly_highlights || content.strengths || [],
      concerns: content.concerns || content.areas_to_improve || content.growth_areas || [],
      encouragement: content.encouragement || content.relationship_note || '',
      evidenceSummary: report.evidence_summary || [],
      limitationNote: report.limitation_note || '',
      safetyHandoff: report.safety_handoff || ''
    }
  },

  normalizeAssessmentTrend(payload) {
    if (!payload) return null
    return {
      latestScore: payload.latest_score,
      changeSummary: payload.change_summary,
      points: (payload.trend_points || []).slice(0, 4).map(item => ({
        id: item.event_id,
        label: (item.submitted_at || '').slice(5, 10) || '本周',
        score: item.total_score,
        summary: item.change_summary || '已记录本次评估'
      })),
      dimensions: (payload.dimension_scores || []).slice(0, 5).map(item => ({
        id: item.id,
        label: item.label,
        score: item.score
      }))
    }
  },

  openAction(e) {
    const path = e.currentTarget.dataset.path
    if (!path) return
    const tabPages = [
      '/pages/home/home',
      '/pages/checkin/checkin',
      '/pages/discover/discover',
      '/pages/report/report',
      '/pages/profile/profile'
    ]
    if (tabPages.includes(path)) {
      wx.switchTab({ url: path })
      return
    }
    wx.navigateTo({ url: path })
  }
})

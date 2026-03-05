/**
 * 报告页 - 关系健康报告
 * 支持日报/周报/月报切换、生成报告、查看历史、趋势图表
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    // 当前选中的报告类型 tab
    currentTab: 'daily',
    tabs: [
      { key: 'daily', label: '日报' },
      { key: 'weekly', label: '周报' },
      { key: 'monthly', label: '月报' }
    ],

    // 当前报告内容
    reportContent: null,
    reportView: null,

    // 历史报告列表
    historyList: [],
    historyListView: [],

    // 趋势数据（占位）
    trendData: null,

    // 加载 & 生成状态
    loading: false,
    generating: false
  },

  onLoad() {
    // 初始化
  },

  onShow() {
    if (!auth.checkLogin()) return
    this.loadHistory()
    this.loadTrend()
  },

  /**
   * 切换报告类型 tab
   */
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      currentTab: tab,
      reportContent: null,
      reportView: null
    })
    this.loadHistory()
  },

  /**
   * 生成报告
   */
  async generateReport() {
    if (this.data.generating) return
    this.setData({ generating: true })

    const urlMap = {
      daily: '/reports/generate-daily',
      weekly: '/reports/generate-weekly',
      monthly: '/reports/generate-monthly'
    }

    const url = urlMap[this.data.currentTab]
    const pairId = auth.getPairId()

    try {
      if (!pairId && this.data.currentTab !== 'daily') {
        wx.showToast({ title: '单人模式仅支持日报', icon: 'none' })
        this.setData({ generating: false })
        return
      }

      const res = pairId
        ? await api.post(`${url}?pair_id=${pairId}`)
        : await api.post(`${url}?mode=solo`)
      this.setData({ reportContent: res, reportView: this.normalizeReport(res) })
      wx.showToast({ title: '报告生成成功', icon: 'success' })
      // 刷新历史列表
      this.loadHistory()
    } catch (e) {
      wx.showToast({ title: e.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ generating: false })
    }
  },

  /**
   * 加载历史报告
   */
  async loadHistory() {
    this.setData({ loading: true })
    try {
      const pairId = auth.getPairId()
      const qs = pairId
        ? `pair_id=${pairId}&report_type=${this.data.currentTab}`
        : `mode=solo`
      const res = await api.get(`/reports/history?${qs}`)
      const list = res || []
      this.setData({
        historyList: list,
        historyListView: list.map(item => ({
          ...item,
          _label: item.type === 'solo' ? '个人日报' : item.type === 'weekly' ? '周报' : item.type === 'monthly' ? '月报' : '日报'
        }))
      })
    } catch (e) {
      console.error('获取报告历史失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载趋势数据
   */
  async loadTrend() {
    try {
      const pairId = auth.getPairId()
      const qs = pairId ? `pair_id=${pairId}` : `mode=solo`
      const res = await api.get(`/reports/trend?${qs}`)
      this.setData({ trendData: res })
    } catch (e) {
      console.error('获取趋势数据失败:', e)
    }
  },

  /**
   * 查看历史报告详情
   */
  viewReport(e) {
    const report = e.currentTarget.dataset.report
    this.setData({ reportContent: report, reportView: this.normalizeReport(report) })
  },

  normalizeReport(report) {
    if (!report) return null
    const content = report.content || {}
    const type = report.type || this.data.currentTab

    const view = {
      title: type === 'solo' ? '个人日报' : (type === 'weekly' ? '周报' : type === 'monthly' ? '月报' : '日报'),
      healthScore: content.health_score || content.overall_health_score || null,
      insight: content.insight || content.self_insight || content.executive_summary || '',
      suggestion: content.suggestion || content.self_care_tip || '',
      highlights: content.highlights || content.weekly_highlights || [],
      concerns: content.concerns || content.areas_to_improve || [],
      encouragement: content.encouragement || content.relationship_note || '',
      trend: content.trend || content.monthly_trend || '',
      raw: content
    }

    return view
  }
})

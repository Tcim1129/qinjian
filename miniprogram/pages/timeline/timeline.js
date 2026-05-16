/**
 * 关系时间轴页面 - 展示关系演变脉络
 * 对接后端 /insights/timeline 和 /insights/timeline/events/{event_id}
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

const CATEGORY_LABELS = {
  checkin: '打卡记录',
  report: '关系简报',
  risk: '风险预警',
  action: '行动任务',
  playbook: '剧本迁移',
  strategy: '策略调整',
  coach: '沟通建议',
  alignment: '双视角对齐',
  crisis: '危机干预',
  task: '任务管理',
  message: '消息预演',
  plan: '干预计划',
  assessment: '周评估',
  repair_protocol: '修复协议',
  client: '端侧预检',
  safety: '安全检测',
}

const TONE_STYLES = {
  warning: { bg: '#FFF3E0', border: '#FF9800', icon: '⚠️' },
  insight: { bg: '#E8F5E9', border: '#4CAF50', icon: '💡' },
  movement: { bg: '#E3F2FD', border: '#2196F3', icon: '🔄' },
  support: { bg: '#FCE4EC', border: '#E91E63', icon: '🤝' },
  progress: { bg: '#E8F5E9', border: '#4CAF50', icon: '✅' },
  neutral: { bg: '#FAFAFA', border: '#BCAAA4', icon: '📝' },
}

Page({
  data: {
    events: [],
    groupedEvents: [],
    loading: true,
    loadingDetail: false,
    selectedEvent: null,
    eventDetail: null,
    showDetailDrawer: false,
    categories: [{ value: 'all', label: '全部类别' }],
    tones: [{ value: 'all', label: '全部语气' }],
    selectedCategory: 'all',
    selectedTone: 'all',
    pairId: null,
    isSolo: false,
    highlights: [],
    eventCount: 0,
    latestEventAt: '',
    currentContext: null,
  },

  onLoad() {
    if (!auth.checkLogin()) return
    const pairId = auth.getPairId()
    this.setData({ pairId, isSolo: !pairId })
    this.loadTimeline()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  onPullDownRefresh() {
    this.loadTimeline().finally(() => wx.stopPullDownRefresh())
  },

  async loadTimeline() {
    this.setData({ loading: true })
    const pairId = this.data.pairId
    try {
      const url = pairId
        ? `/insights/timeline?pair_id=${pairId}&limit=30`
        : '/insights/timeline?mode=solo&limit=30'
      const res = await api.get(url)
      const events = (res.events || []).map(e => this.enrichEvent(e))
      const grouped = this.groupByDate(events)
      const categories = this.extractCategories(events)
      const tones = this.extractTones(events)

      this.setData({
        events,
        groupedEvents: grouped,
        highlights: res.highlights || [],
        eventCount: res.event_count || 0,
        latestEventAt: res.latest_event_at ? this.formatDate(res.latest_event_at) : '',
        categories,
        tones,
        loading: false,
      })
    } catch (e) {
      console.error('获取时间轴失败:', e)
      this.setData({ loading: false, events: [], groupedEvents: [] })
      if (e.code !== 404 && e.code !== 403) {
        wx.showToast({ title: '时间轴加载失败', icon: 'none' })
      }
    }
  },

  enrichEvent(event) {
    const tone = event.tone || 'neutral'
    const style = TONE_STYLES[tone] || TONE_STYLES.neutral
    return {
      ...event,
      categoryLabel: CATEGORY_LABELS[event.category] || event.category_label || event.category,
      toneStyle: style,
      timeLabel: this.formatTimeLabel(event.occurred_at),
      dateKey: this.formatDateKey(event.occurred_at),
    }
  },

  groupByDate(events) {
    const groups = []
    const bucket = new Map()
    for (const event of events) {
      const key = event.dateKey
      if (!bucket.has(key)) {
        bucket.set(key, [])
        groups.push({ date: key, events: bucket.get(key) })
      }
      bucket.get(key).push(event)
    }
    return groups
  },

  extractCategories(events) {
    const cats = [{ value: 'all', label: '全部类别' }]
    const seen = new Set()
    for (const e of events) {
      if (e.category && !seen.has(e.category)) {
        seen.add(e.category)
        cats.push({ value: e.category, label: e.categoryLabel })
      }
    }
    return cats
  },

  extractTones(events) {
    const tns = [{ value: 'all', label: '全部语气' }]
    const seen = new Set()
    for (const e of events) {
      if (e.tone && !seen.has(e.tone)) {
        seen.add(e.tone)
        tns.push({ value: e.tone, label: e.tone_label || e.tone })
      }
    }
    return tns
  },

  filterEvents() {
    const { events, selectedCategory, selectedTone } = this.data
    let filtered = events
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(e => e.category === selectedCategory)
    }
    if (selectedTone !== 'all') {
      filtered = filtered.filter(e => e.tone === selectedTone)
    }
    this.setData({ groupedEvents: this.groupByDate(filtered) })
  },

  onCategoryChange(e) {
    this.setData({ selectedCategory: e.currentTarget.dataset.value }, () => this.filterEvents())
  },

  onToneChange(e) {
    this.setData({ selectedTone: e.currentTarget.dataset.value }, () => this.filterEvents())
  },

  async onEventTap(e) {
    const eventId = e.currentTarget.dataset.id
    if (!eventId) return
    this.setData({ loadingDetail: true, showDetailDrawer: true })
    try {
      const res = await api.get(`/insights/timeline/events/${eventId}`)
      const detail = {
        event: res.event,
        summary: res.event_summary,
        metrics: res.metrics || [],
        evidenceCards: res.evidence_cards || [],
        impactModules: res.impact_modules || [],
        recommendedNextAction: res.recommended_next_action,
        currentContext: res.current_context,
      }
      this.setData({ eventDetail: detail, loadingDetail: false })
    } catch (e) {
      console.error('获取事件详情失败:', e)
      this.setData({ loadingDetail: false })
      wx.showToast({ title: '详情加载失败', icon: 'none' })
    }
  },

  closeDetailDrawer() {
    this.setData({ showDetailDrawer: false, eventDetail: null })
  },

  formatDate(isoStr) {
    if (!isoStr) return ''
    const d = new Date(isoStr)
    const m = d.getMonth() + 1
    const day = d.getDate()
    return `${m}月${day}日`
  },

  formatDateKey(isoStr) {
    if (!isoStr) return '未知'
    const d = new Date(isoStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  },

  formatTimeLabel(isoStr) {
    if (!isoStr) return ''
    const d = new Date(isoStr)
    const h = d.getHours()
    const m = d.getMinutes()
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
  },

  goBack() {
    wx.navigateBack()
  },

  goCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  goCrisis() {
    const pairId = this.data.pairId
    if (pairId) {
      wx.navigateTo({ url: '/pages/crisis/crisis' })
    }
  },
})

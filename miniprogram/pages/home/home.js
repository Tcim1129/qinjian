/**
 * 首页 - 比赛主链主页
 * 聚焦记录、体检、报告、时间轴四条主线
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')
const { syncUserAndPair, normalizePair } = require('../../utils/user-sync.js')

function normalizeAssessment(payload) {
  if (!payload) return null
  const score = Number(payload.total_score || 0)
  let levelLabel = '继续记录，系统会逐步形成更稳定的判断'

  if (score >= 82) {
    levelLabel = '这周状态很稳，可以做更深的表达'
  } else if (score >= 65) {
    levelLabel = '整体可修复，适合继续轻量推进'
  } else if (score >= 48) {
    levelLabel = '建议先减压，再谈更难的话题'
  } else {
    levelLabel = '先把安全感和边界放回前面'
  }

  return {
    totalScore: score,
    levelLabel,
    submittedAt: payload.submitted_at || '',
    changeSummary: payload.change_summary || '系统已经记录这次正式体检。'
  }
}

function normalizeReport(payload) {
  if (!payload) return null
  const content = payload.content || {}
  return {
    title: payload.type === 'weekly' ? '最新周报' : payload.type === 'monthly' ? '最新月报' : '最新日报',
    healthScore: content.health_score || content.overall_health_score || '--',
    insight: content.insight || content.self_insight || content.executive_summary || '继续记录，系统会逐步给出更完整的判断。'
  }
}

Page({
  data: {
    userInfo: null,
    pairInfo: null,
    pairDisplayName: '伴侣',
    greeting: '',
    todayCheckin: null,
    hasCheckedIn: false,
    streak: 0,
    crisisStatus: null,
    hasCrisis: false,
    latestAssessment: null,
    latestReport: null,
    loading: true
  },

  onLoad() {
    this.setGreeting()
  },

  onShow() {
    if (!auth.checkLogin()) return
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
    this.setGreeting()
    this.loadHomeData()
  },

  onPullDownRefresh() {
    this.loadHomeData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  setGreeting() {
    const hour = new Date().getHours()
    const userInfo = auth.getUserInfo()
    const name = (userInfo && userInfo.nickname) || '亲爱的'
    let greetText = ''

    if (hour < 6) {
      greetText = '夜深了'
    } else if (hour < 9) {
      greetText = '早上好'
    } else if (hour < 12) {
      greetText = '上午好'
    } else if (hour < 14) {
      greetText = '中午好'
    } else if (hour < 18) {
      greetText = '下午好'
    } else if (hour < 22) {
      greetText = '晚上好'
    } else {
      greetText = '夜深了'
    }

    this.setData({
      greeting: `${greetText}，${name}`,
      userInfo
    })
  },

  async loadHomeData() {
    this.setData({ loading: true })

    const app = getApp()
    let pairInfo = app.globalData.pairInfo
    try {
      const synced = await syncUserAndPair()
      pairInfo = synced.pairInfo
    } catch (error) {
      console.warn('首页同步配对信息失败', error)
    }

    const pairId = pairInfo ? (pairInfo.id || pairInfo.pair_id) : null
    const normalizedPair = normalizePair(pairInfo)
    const displayName = normalizedPair && (normalizedPair.partner_nickname || normalizedPair.partner_name || normalizedPair.partnerNickname)

    this.setData({
      pairInfo: normalizedPair,
      pairDisplayName: displayName || '伴侣'
    })

    const tasks = [
      this.loadTodayCheckin(pairId),
      this.loadStreak(pairId),
      this.loadLatestAssessment(pairId),
      this.loadLatestReport(pairId)
    ]

    if (pairId) {
      tasks.push(this.loadCrisisStatus(pairId))
    } else {
      this.setData({ crisisStatus: null, hasCrisis: false })
    }

    try {
      await Promise.allSettled(tasks)
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadTodayCheckin(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    const url = resolvedPairId ? `/checkins/today?pair_id=${resolvedPairId}` : '/checkins/today?mode=solo'

    try {
      const res = await api.get(url)
      this.setData({
        todayCheckin: res.my_checkin || res,
        hasCheckedIn: !!(res && res.my_done)
      })
    } catch (error) {
      this.setData({ todayCheckin: null, hasCheckedIn: false })
      if (error.code !== 404) {
        console.error('获取今日记录失败:', error)
      }
    }
  },

  async loadStreak(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    const url = resolvedPairId ? `/checkins/streak?pair_id=${resolvedPairId}` : '/checkins/streak?mode=solo'

    try {
      const res = await api.get(url)
      this.setData({ streak: res.streak || 0 })
    } catch (error) {
      this.setData({ streak: 0 })
      console.error('获取记录天数失败:', error)
    }
  },

  async loadLatestAssessment(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    try {
      const res = await api.getWeeklyAssessmentLatest(resolvedPairId)
      this.setData({ latestAssessment: normalizeAssessment(res) })
    } catch (error) {
      this.setData({ latestAssessment: null })
      console.warn('获取体检结果失败', error)
    }
  },

  async loadLatestReport(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    const dailyUrl = resolvedPairId
      ? `/reports/latest?pair_id=${resolvedPairId}&report_type=daily`
      : '/reports/latest?mode=solo&report_type=daily'
    const weeklyUrl = resolvedPairId
      ? `/reports/latest?pair_id=${resolvedPairId}&report_type=weekly`
      : '/reports/latest?mode=solo&report_type=weekly'

    try {
      let res = await api.get(dailyUrl).catch(() => null)
      if (!res) {
        res = await api.get(weeklyUrl).catch(() => null)
      }
      this.setData({ latestReport: normalizeReport(res) })
    } catch (error) {
      this.setData({ latestReport: null })
      console.warn('获取最新报告失败', error)
    }
  },

  async loadCrisisStatus(pairId) {
    try {
      const res = await api.get(`/crisis/status/${pairId}`)
      this.setData({
        crisisStatus: res,
        hasCrisis: !!(res && res.crisis_level && res.crisis_level !== 'none')
      })
    } catch (error) {
      this.setData({ crisisStatus: null, hasCrisis: false })
      console.error('获取危机状态失败:', error)
    }
  },

  goCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  goHealthTest() {
    wx.switchTab({ url: '/pages/discover/discover' })
  },

  goReport() {
    wx.switchTab({ url: '/pages/report/report' })
  },

  goTree() {
    wx.navigateTo({ url: '/pages/tree/tree' })
  },

  goCrisis() {
    wx.navigateTo({ url: '/pages/crisis/crisis' })
  },

  goPair() {
    wx.navigateTo({ url: '/pages/pair/pair' })
  },

  goTimeline() {
    wx.navigateTo({ url: '/pages/timeline/timeline' })
  },

  goNotification() {
    wx.navigateTo({ url: '/pages/notification/notification' })
  },

  goPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' })
  }
})

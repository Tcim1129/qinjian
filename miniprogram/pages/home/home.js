/**
 * 首页 - 亲健核心主页
 * 展示用户问候、配对状态、今日心情摘要、快捷操作、连续打卡天数、危机提醒
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')
const { syncUserAndPair, normalizePair } = require('../../utils/user-sync.js')

Page({
  data: {
    // 用户信息
    userInfo: null,
    pairInfo: null,
    pairDisplayName: '伴侣',
    greeting: '',

    // 今日打卡状态
    todayCheckin: null,
    hasCheckedIn: false,

    // 连续打卡天数
    streak: 0,

    // 关系树状态
    treeStatus: null,

    // 危机预警
    crisisStatus: null,
    hasCrisis: false,

    // 加载状态
    loading: true
  },

  onLoad() {
    this.setGreeting()
  },

  /**
   * 页面显示时刷新数据
   * 每次切回首页都重新拉取最新状态
   */
  onShow() {
    if (!auth.checkLogin()) return
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
    this.setGreeting()
    this.loadHomeData()
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.loadHomeData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  /**
   * 根据时间段设置问候语
   */
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
      userInfo: userInfo
    })
  },

  /**
   * 并行加载首页所有数据
   */
  async loadHomeData() {
    this.setData({ loading: true })

    const app = getApp()
    let pairInfo = app.globalData.pairInfo
    try {
      const synced = await syncUserAndPair()
      pairInfo = synced.pairInfo
    } catch (e) {
      console.warn('首页拉取配对信息失败', e)
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
      this.loadTreeStatus(pairId)
    ]
    if (pairId) {
      tasks.push(this.loadCrisisStatus(pairId))
    }

    try {
      await Promise.allSettled(tasks)
    } catch (e) {
      console.error('首页数据加载异常:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 获取今日打卡记录
   */
  async loadTodayCheckin(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    const url = resolvedPairId ? `/checkins/today?pair_id=${resolvedPairId}` : '/checkins/today?mode=solo'
    try {
      const res = await api.get(url)
      const myDone = res && res.my_done
      this.setData({
        todayCheckin: res.my_checkin || res,
        hasCheckedIn: !!myDone
      })
    } catch (e) {
      if (e.code === 404) {
        this.setData({ todayCheckin: null, hasCheckedIn: false })
      } else {
        console.error('获取今日打卡失败:', e)
      }
    }
  },

  async loadStreak(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    const url = resolvedPairId ? `/checkins/streak?pair_id=${resolvedPairId}` : '/checkins/streak?mode=solo'
    try {
      const res = await api.get(url)
      this.setData({ streak: res.streak || 0 })
    } catch (e) {
      console.error('获取打卡天数失败:', e)
    }
  },

  async loadTreeStatus(pairId = null) {
    const resolvedPairId = pairId === undefined || pairId === null ? auth.getPairId() : pairId
    if (!resolvedPairId) {
      this.setData({ treeStatus: null })
      return
    }
    try {
      const res = await api.get(`/tree/status?pair_id=${resolvedPairId}`)
      this.setData({ treeStatus: res })
    } catch (e) {
      if (e.code === 403 || e.code === 404) {
        const app = getApp()
        app.setPairInfo(null)
        this.setData({ pairInfo: null, pairDisplayName: '伴侣', treeStatus: null })
        return
      }
      console.error('获取关系树状态失败:', e)
    }
  },

  /**
   * 获取危机预警状态
   * @param {string} pairId - 配对ID
   */
  async loadCrisisStatus(pairId) {
    try {
      const res = await api.get(`/crisis/status/${pairId}`)
      this.setData({
        crisisStatus: res,
        hasCrisis: res && res.crisis_level && res.crisis_level !== 'none'
      })
    } catch (e) {
      if (e.code === 403 || e.code === 404) {
        const app = getApp()
        app.setPairInfo(null)
        this.setData({ pairInfo: null, pairDisplayName: '伴侣', crisisStatus: null, hasCrisis: false })
        return
      }
      console.error('获取危机状态失败:', e)
    }
  },

  /**
   * 跳转到打卡页
   */
  goCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  /**
   * 跳转到报告页
   */
  goReport() {
    wx.switchTab({ url: '/pages/report/report' })
  },

  /**
   * 跳转到关系树
   */
  goTree() {
    wx.navigateTo({ url: '/pages/tree/tree' })
  },

  /**
   * 跳转到危机详情
   */
  goCrisis() {
    wx.navigateTo({ url: '/pages/crisis/crisis' })
  },

  /**
   * 跳转到配对页面
   */
  goPair() {
    wx.navigateTo({ url: '/pages/pair/pair' })
  }
})

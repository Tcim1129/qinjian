/**
 * 个人中心页 - 账号、关系状态与设置入口
 */
const auth = require('../../utils/auth.js')
const api = require('../../utils/api.js')
const { syncUserAndPair, normalizePair } = require('../../utils/user-sync.js')

function normalizeAssessment(payload) {
  if (!payload) return null
  const score = Number(payload.total_score || 0)
  let levelLabel = '继续记录中'

  if (score >= 82) {
    levelLabel = '状态很稳'
  } else if (score >= 65) {
    levelLabel = '整体可修复'
  } else if (score >= 48) {
    levelLabel = '建议先减压'
  } else {
    levelLabel = '需要更多支持'
  }

  return {
    totalScore: score,
    levelLabel
  }
}

Page({
  data: {
    userInfo: null,
    pairInfo: null,
    isPaired: false,
    assessmentLatest: null,
    privacyStatus: null
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 })
    }
    this.refreshData()
  },

  async refreshData() {
    try {
      const synced = await syncUserAndPair()
      this.setData({
        userInfo: synced.userInfo,
        pairInfo: normalizePair(synced.pairInfo),
        isPaired: !!(synced.summary && synced.summary.is_paired)
      })
      if (!synced.summary) {
        this.loadLocalData()
      }
    } catch (error) {
      console.warn('Profile 拉取状态失败', error)
      this.loadLocalData()
    }

    await this.loadInsights()
  },

  async loadInsights() {
    const pairId = auth.getPairId()
    try {
      const [assessmentLatest, privacyStatus] = await Promise.all([
        api.getWeeklyAssessmentLatest(pairId).catch(() => null),
        api.getPrivacyStatus().catch(() => null)
      ])
      this.setData({
        assessmentLatest: normalizeAssessment(assessmentLatest),
        privacyStatus
      })
    } catch (error) {
      console.warn('Profile insight load failed', error)
    }
  },

  loadLocalData() {
    const app = getApp()
    const userInfo = app.globalData.userInfo
    const pairInfo = normalizePair(app.globalData.pairInfo)

    this.setData({
      userInfo,
      pairInfo,
      isPaired: !!(pairInfo && pairInfo.status === 'active' && (pairInfo.id || pairInfo.pair_id))
    })
  },

  openPage(e) {
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
  },

  handleLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      confirmColor: '#214B8F',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.logout()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  },

  showAbout() {
    wx.showModal({
      title: '关于亲健',
      content: '亲健 v2.8.0\\n青年亲密关系健康支持系统\\n把记录、体检、报告和修复建议串成一条主线。',
      showCancel: false,
      confirmColor: '#214B8F'
    })
  },

  editName() {
    wx.showModal({
      title: '修改昵称',
      editable: true,
      placeholderText: '输入新的昵称',
      content: (this.data.userInfo && this.data.userInfo.nickname) || '',
      success: async (res) => {
        if (!res.confirm) return
        const nickname = (res.content || '').trim()
        if (!nickname) {
          wx.showToast({ title: '昵称不能为空', icon: 'none' })
          return
        }
        try {
          const updated = await api.put('/auth/me', { nickname })
          const app = getApp()
          app.globalData.userInfo = updated
          this.setData({ userInfo: updated })
          wx.showToast({ title: '昵称已更新', icon: 'success' })
        } catch (error) {
          wx.showToast({ title: error.message || '保存失败', icon: 'none' })
        }
      }
    })
  },

  changePassword() {
    wx.showToast({ title: '请在网页版或 App 中修改密码', icon: 'none' })
  }
})

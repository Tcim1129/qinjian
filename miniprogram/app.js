let config

try {
  config = require('./config.js')
} catch (error) {
  config = require('./config.template.js')
}

/**
 * 亲健小程序 - 全局入口
 * 青年亲密关系健康管理专家
 * "让爱有据可循"
 */
App({
  globalData: {
    userInfo: null,
    pairInfo: null,
    token: null,
    isLoggedIn: false,
    baseUrl: config.baseUrl,
    appName: config.appName || '亲健'
  },

  onLaunch() {
    // 从本地缓存读取登录态
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    const pairInfo = wx.getStorageSync('pairInfo')

    if (token) {
      this.globalData.token = token
      this.globalData.isLoggedIn = true
    }
    if (userInfo) {
      this.globalData.userInfo = userInfo
    }
    if (pairInfo) {
      this.globalData.pairInfo = pairInfo
    }

    // 验证 token 有效性
    if (token) {
      this.checkTokenValid()
    }
  },

  async syncPairState() {
    const api = require('./utils/api.js')
    try {
      const summary = await api.get('/pairs/summary')
      const activePair = summary && summary.is_paired && summary.active_pair && summary.active_pair.status === 'active'
        ? summary.active_pair
        : null
      this.setPairInfo(activePair)
      return summary
    } catch (e) {
      this.setPairInfo(null)
      return null
    }
  },

  /**
   * 检查 token 是否有效
   */
  checkTokenValid() {
    const api = require('./utils/api.js')
    api.get('/auth/me').then(res => {
      this.globalData.userInfo = res
      wx.setStorageSync('userInfo', res)
      return this.syncPairState()
    }).catch(() => {
      // token 失效，清除登录态
      this.logout()
    })
  },

  /**
   * 设置登录态
   */
  setLoginState(token, userInfo) {
    this.globalData.token = token
    this.globalData.userInfo = userInfo
    this.globalData.pairInfo = null
    this.globalData.isLoggedIn = true
    wx.setStorageSync('token', token)
    wx.setStorageSync('userInfo', userInfo)
    wx.removeStorageSync('pairInfo')
  },

  /**
   * 设置配对信息
   */
  setPairInfo(pairInfo) {
    this.globalData.pairInfo = pairInfo || null
    if (pairInfo) {
      wx.setStorageSync('pairInfo', pairInfo)
      return
    }

    wx.removeStorageSync('pairInfo')
  },

  /**
   * 退出登录
   */
  logout() {
    this.globalData.token = null
    this.globalData.userInfo = null
    this.globalData.pairInfo = null
    this.globalData.isLoggedIn = false
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    wx.removeStorageSync('pairInfo')
  },

  /**
   * 检查是否已登录，未登录则跳转登录页
   */
  checkLogin() {
    if (!this.globalData.isLoggedIn) {
      wx.navigateTo({ url: '/pages/login/login' })
      return false
    }
    return true
  },

  /**
   * 检查是否已配对
   */
  checkPaired() {
    return !!this.globalData.pairInfo
  }
})

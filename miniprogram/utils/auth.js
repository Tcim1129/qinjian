/**
 * 用户认证与授权工具模块
 */

/**
 * 检查用户是否已登录
 * 未登录时自动跳转到登录页
 * @returns {boolean} 是否已登录
 */
function checkLogin() {
  const app = getApp()
  if (!app || !app.globalData) return false

  const token = app.globalData.token

  if (!token) {
    wx.reLaunch({
      url: '/pages/login/login'
    })
    return false
  }

  return true
}

/**
 * 检查用户是否已配对
 * 未配对时弹出提示
 * @returns {boolean} 是否已配对
 */
function checkPaired() {
  const app = getApp()
  if (!app || !app.globalData) return false

  const pairInfo = app.globalData.pairInfo

  if (!pairInfo || (!pairInfo.id && !pairInfo.pair_id)) {
    wx.showToast({
      title: '请先完成配对',
      icon: 'none',
      duration: 2000
    })
    return false
  }

  return true
}

function getUserInfo() {
  const app = getApp()
  if (!app || !app.globalData) return null

  return app.globalData.userInfo || null
}

function getPairId() {
  const app = getApp()
  if (!app || !app.globalData) return null

  const pairInfo = app.globalData.pairInfo
  if (!pairInfo) return null
  return pairInfo.id || pairInfo.pair_id || null
}

module.exports = {
  checkLogin,
  checkPaired,
  getUserInfo,
  getPairId
}

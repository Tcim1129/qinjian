const api = require('./api.js')

function normalizePair(pair) {
  if (!pair) return null
  const partnerName = pair.custom_partner_nickname || pair.partner_nickname || pair.partner_name || pair.partnerNickname || '伴侣'
  return {
    ...pair,
    partner_name: partnerName,
    partnerNickname: partnerName,
    partner_nickname: partnerName,
  }
}

function getActivePair(summary) {
  if (!summary || !summary.is_paired || !summary.active_pair) return null
  if (summary.active_pair.status !== 'active') return null
  return normalizePair(summary.active_pair)
}

async function syncUserAndPair() {
  const app = getApp()
  if (!app || !app.globalData || !app.globalData.token) {
    return { userInfo: null, pairInfo: null, summary: null }
  }

  const [meResult, summaryResult] = await Promise.allSettled([
    api.get('/auth/me'),
    api.get('/pairs/summary'),
  ])

  let userInfo = app.globalData.userInfo || null
  let pairInfo = app.globalData.pairInfo || null
  let summary = null

  if (meResult.status === 'fulfilled') {
    userInfo = meResult.value
    app.globalData.userInfo = userInfo
    wx.setStorageSync('userInfo', userInfo)
  }

  if (summaryResult.status === 'fulfilled') {
    summary = summaryResult.value
    pairInfo = getActivePair(summary)
    app.setPairInfo(pairInfo)
  }

  return { userInfo, pairInfo, summary }
}

module.exports = {
  syncUserAndPair,
  normalizePair,
  getActivePair,
}

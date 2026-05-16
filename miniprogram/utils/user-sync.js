const api = require('./api.js')

const PAIR_SUMMARY_RETRY_COOLDOWN_MS = 60 * 1000
let pairSummaryRetryAfter = 0

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

  const shouldSkipPairSummary = Date.now() < pairSummaryRetryAfter
  const [meResult, summaryResult] = await Promise.allSettled([
    api.get('/auth/me'),
    shouldSkipPairSummary ? Promise.resolve(null) : api.get('/pairs/summary'),
  ])

  let userInfo = app.globalData.userInfo || null
  let pairInfo = app.globalData.pairInfo || null
  let summary = null

  if (meResult.status === 'fulfilled') {
    userInfo = meResult.value
    app.globalData.userInfo = userInfo
  }

  if (summaryResult.status === 'fulfilled' && summaryResult.value) {
    summary = summaryResult.value
    pairInfo = getActivePair(summary)
    app.setPairInfo(pairInfo)
    pairSummaryRetryAfter = 0
  } else if (
    summaryResult.status === 'rejected' &&
    summaryResult.reason &&
    (summaryResult.reason.code >= 500 || summaryResult.reason.network || summaryResult.reason.timeout)
  ) {
    pairSummaryRetryAfter = Date.now() + PAIR_SUMMARY_RETRY_COOLDOWN_MS
  }

  return { userInfo, pairInfo, summary }
}

module.exports = {
  syncUserAndPair,
  normalizePair,
  getActivePair,
}

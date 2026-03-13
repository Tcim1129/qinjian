import api from './api.js'

const USER_KEY = 'qj_app_user'
const PAIR_SUMMARY_KEY = 'qj_app_pair_summary'

export function normalizePair(pair) {
  if (!pair) return null
  const partnerName = pair.custom_partner_nickname || pair.partner_nickname || pair.partner_name || pair.partnerNickname || '陪伴对象'
  return {
    ...pair,
    partner_name: partnerName,
    partnerNickname: partnerName,
    partner_nickname: partnerName,
  }
}

export function loadCachedSession() {
  const userInfo = uni.getStorageSync(USER_KEY) || null
  const pairSummary = uni.getStorageSync(PAIR_SUMMARY_KEY) || null
  return {
    userInfo,
    pairSummary: pairSummary ? {
      ...pairSummary,
      active_pair: normalizePair(pairSummary.active_pair),
    } : null,
  }
}

export function persistSession(userInfo, pairSummary) {
  if (userInfo) {
    uni.setStorageSync(USER_KEY, userInfo)
  } else {
    uni.removeStorageSync(USER_KEY)
  }

  if (pairSummary) {
    uni.setStorageSync(PAIR_SUMMARY_KEY, pairSummary)
  } else {
    uni.removeStorageSync(PAIR_SUMMARY_KEY)
  }
}

export function normalizeSummary(summary) {
  if (!summary) return null
  return {
    ...summary,
    active_pair: normalizePair(summary.active_pair),
  }
}

export async function syncSession(store) {
  if (!api.isLoggedIn()) {
    persistSession(null, null)
    store.commit('SET_USER_INFO', null)
    store.commit('SET_PAIR_SUMMARY', null)
    return null
  }

  const [me, summary] = await Promise.all([
    api.getMe(),
    api.getPairSummary(),
  ])
  const normalizedSummary = normalizeSummary(summary)
  persistSession(me, normalizedSummary)
  store.commit('SET_USER_INFO', me)
  store.commit('SET_PAIR_SUMMARY', normalizedSummary)
  return { me, summary: normalizedSummary }
}

import api from './api.js'

const USER_KEY = 'qj_app_user'
const PAIR_SUMMARY_KEY = 'qj_app_pair_summary'

let volatileUserInfo = null
let volatilePairSummary = null
let legacyStorageCleared = false

function clearLegacySessionStorage() {
  if (legacyStorageCleared) return
  legacyStorageCleared = true
  uni.removeStorageSync(USER_KEY)
  uni.removeStorageSync(PAIR_SUMMARY_KEY)
}

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

function normalizeActivePair(summary) {
  if (!summary || !summary.is_paired || !summary.active_pair) return null
  if (summary.active_pair.status !== 'active') return null
  return normalizePair(summary.active_pair)
}

export function loadCachedSession() {
  clearLegacySessionStorage()
  const userInfo = volatileUserInfo
  const pairSummary = volatilePairSummary
  return {
    userInfo,
    pairSummary: pairSummary ? {
      ...pairSummary,
      active_pair: normalizeActivePair(pairSummary),
    } : null,
  }
}

export function persistSession(userInfo, pairSummary) {
  clearLegacySessionStorage()
  volatileUserInfo = userInfo || null
  volatilePairSummary = pairSummary || null
}

export function normalizeSummary(summary) {
  if (!summary) return null
  return {
    ...summary,
    active_pair: normalizeActivePair(summary),
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

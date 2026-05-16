import api from './api.js'

const USER_KEY = 'qj_app_user'
const PAIR_SUMMARY_KEY = 'qj_app_pair_summary'

let volatileUserInfo = null
let volatilePairSummary = null
let legacyStorageCleared = false

function getUniLike() {
  if (typeof globalThis !== 'undefined' && globalThis.uni) {
    return globalThis.uni
  }
  return {
    getStorageSync(key) {
      try {
        return globalThis?.localStorage?.getItem?.(key)
      } catch (_) {
        return ''
      }
    },
    setStorageSync(key, value) {
      try {
        globalThis?.localStorage?.setItem?.(key, value)
      } catch (_) {
        // ignore
      }
    },
    removeStorageSync(key) {
      try {
        globalThis?.localStorage?.removeItem?.(key)
      } catch (_) {
        // ignore
      }
    },
  }
}

function clearLegacySessionStorage() {
  if (legacyStorageCleared) return
  legacyStorageCleared = true
}

function safeParse(value) {
  if (!value) return null
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch (_) {
    return null
  }
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
  const uniLike = getUniLike()
  const userInfo = volatileUserInfo || safeParse(uniLike.getStorageSync(USER_KEY))
  const pairSummary = volatilePairSummary || safeParse(uniLike.getStorageSync(PAIR_SUMMARY_KEY))
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
  const uniLike = getUniLike()
  if (volatileUserInfo) {
    uniLike.setStorageSync(USER_KEY, JSON.stringify(volatileUserInfo))
  } else {
    uniLike.removeStorageSync(USER_KEY)
  }
  if (volatilePairSummary) {
    uniLike.setStorageSync(PAIR_SUMMARY_KEY, JSON.stringify(volatilePairSummary))
  } else {
    uniLike.removeStorageSync(PAIR_SUMMARY_KEY)
  }
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

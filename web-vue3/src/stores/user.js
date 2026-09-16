import { defineStore } from 'pinia'
import { api } from '@/api'
import { ref, computed, watch } from 'vue'
import { useHomeStore } from '@/stores/home'
import { useReportStore } from '@/stores/report'
import { useCheckinStore } from '@/stores/checkin'
import { DEMO_TOKEN, cloneDemo, demoFixture } from '@/demo/fixtures'
import { setRefreshAttemptGuardBypass } from '@/utils/refreshGuards'
import { setStorageOwner, clearStorageOwner } from '@/utils/accountStorage'

export const useUserStore = defineStore('user', () => {
  const me = ref(null)
  const token = ref(sessionStorage.getItem('qj_token') || '')
  const pairs = ref([])
  const currentPair = ref(null)
  const notifications = ref([])
  watch(token, () => {
    clearStorageOwner()
    useHomeStore().reset()
    useReportStore().reset()
    useCheckinStore().reset()
  }, { flush: 'sync' })

  const isLoggedIn = computed(() => Boolean(token.value))
  const isDemoMode = computed(() => token.value === DEMO_TOKEN)
  const testingUnrestricted = computed(() => Boolean(me.value?.testing_unrestricted))
  const activePair = computed(() => {
    if (currentPair.value?.status === 'active') return currentPair.value
    return pairs.value.find((pair) => pair.status === 'active') || null
  })
  const hasActivePair = computed(() => Boolean(activePair.value))
  const activePairId = computed(() => activePair.value?.id || '')
  const currentPairId = computed(() => currentPair.value?.id || '')
  const partnerName = computed(() => {
    const pair = activePair.value || currentPair.value
    if (!pair) return ''
    return pair.custom_partner_nickname
      || pair.partner_nickname
      || pair.partner_email
      || pair.partner_phone
      || '对方'
  })

  function syncTestingUnrestrictedBypass() {
    setRefreshAttemptGuardBypass(testingUnrestricted.value)
  }

  async function login(email, password) {
    const res = await api.login(email, password)
    token.value = res.access_token
    api.setToken(res.access_token)
    await bootstrap()
    return res
  }

  async function register(email, nickname, password) {
    const res = await api.register(email, nickname, password)
    token.value = res.access_token
    api.setToken(res.access_token)
    await bootstrap()
    return res
  }

  async function phoneLogin(phone, code) {
    const res = await api.phoneLogin(phone, code)
    token.value = res.access_token
    api.setToken(res.access_token)
    await bootstrap()
    return res
  }

  function logout() {
    clearStorageOwner()
    token.value = ''
    me.value = null
    pairs.value = []
    currentPair.value = null
    notifications.value = []
    syncTestingUnrestrictedBypass()
    api.clearToken()
  }

  function applyDemo() {
    token.value = DEMO_TOKEN
    api.setToken(DEMO_TOKEN)
    me.value = cloneDemo(demoFixture.me)
    setStorageOwner(me.value.id, token.value)
    pairs.value = cloneDemo(demoFixture.pairs)
    currentPair.value = pairs.value.find((p) => p.id === demoFixture.currentPairId) || pairs.value[0] || null
    notifications.value = cloneDemo(demoFixture.notifications)
    syncTestingUnrestrictedBypass()
  }

  function enterDemo(targetPairId = null) {
    applyDemo()
    const chosenId = targetPairId || demoFixture.currentPairId
    const pair = pairs.value.find((p) => p.id === chosenId)
    if (pair) {
      currentPair.value = pair
    }
    localStorage.setItem('qj_current_pair', chosenId)
  }

  async function fetchMe() {
    const requestToken = token.value
    const result = await api.getMe()
    if (requestToken !== token.value) return null
    me.value = result
    setStorageOwner(me.value.id, requestToken)
    syncTestingUnrestrictedBypass()
    return me.value
  }

  async function updateMe(payload = {}) {
    const requestToken = token.value
    const previousNickname = String(me.value?.nickname || '')
    const hasNicknameUpdate = Object.prototype.hasOwnProperty.call(payload, 'nickname')

    if (token.value === DEMO_TOKEN) {
      me.value = {
        ...(me.value || {}),
        ...payload,
      }
      syncTestingUnrestrictedBypass()
      return me.value
    }

    const updated = await api.updateMe(payload)
    if (requestToken !== token.value) return null
    me.value = updated
    syncTestingUnrestrictedBypass()

    if (hasNicknameUpdate && String(me.value?.nickname || '') !== previousNickname) {
      await refreshNicknameReferences()
    }

    return me.value
  }

  async function refreshNicknameReferences() {
    if (!isLoggedIn.value || token.value === DEMO_TOKEN) return
    await Promise.allSettled([fetchPairs(), loadNotifications()])
  }

  async function fetchPairs() {
    const requestToken = token.value
    const result = await api.getMyPairs()
    if (requestToken !== token.value) return []
    pairs.value = result
    const storedId = localStorage.getItem('qj_current_pair')
    const active = pairs.value.filter((p) => p.status === 'active')
    const pending = pairs.value.filter((p) => p.status === 'pending')
    currentPair.value = active.find((p) => p.id === storedId)
      || active[0]
      || pending.find((p) => p.id === storedId)
      || pending[0]
      || null
    return pairs.value
  }

  function upsertPair(pair) {
    if (!pair?.id) return pair
    if (pair.status === 'ended') {
      pairs.value = pairs.value.filter((item) => item.id !== pair.id)
      if (currentPair.value?.id === pair.id) {
        const storedId = localStorage.getItem('qj_current_pair')
        const active = pairs.value.filter((item) => item.status === 'active')
        const pending = pairs.value.filter((item) => item.status === 'pending')
        currentPair.value = active.find((item) => item.id === storedId)
          || active[0]
          || pending.find((item) => item.id === storedId)
          || pending[0]
          || null
      }
      return pair
    }
    const exists = pairs.value.some((item) => item.id === pair.id)
    pairs.value = exists
      ? pairs.value.map((item) => (item.id === pair.id ? pair : item))
      : [...pairs.value, pair]
    if (currentPair.value?.id === pair.id) {
      currentPair.value = pair
    }
    return pair
  }

  function syncPairBundle(res) {
    if (res?.pair) {
      upsertPair(res.pair)
    }
    return res
  }

  async function switchPair(pairId) {
    const match = pairs.value.find((p) => p.id === pairId)
    if (match) {
      currentPair.value = match
      localStorage.setItem('qj_current_pair', pairId)
    }
  }

  async function createPair(type) {
    const requestToken = token.value
    const pair = await api.createPair(type)
    if (requestToken !== token.value) return null
    pairs.value = [...pairs.value.filter((p) => p.id !== pair.id), pair]
    currentPair.value = pair
    return pair
  }

  async function previewJoinPair(code) {
    return api.previewJoinPair(code)
  }

  async function joinPair(code, type) {
    const requestToken = token.value
    const res = await api.joinPair(code, type)
    if (requestToken !== token.value) return null
    await fetchPairs()
    await loadNotifications()
    return res
  }

  async function refreshPairInviteCode(pairId) {
    const requestToken = token.value
    const pair = await api.refreshPairInviteCode(pairId)
    if (requestToken !== token.value) return null
    return upsertPair(pair)
  }

  async function requestPairTypeChange(pairId, type) {
    const requestToken = token.value
    const res = await api.requestPairTypeChange(pairId, type)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function createBreakRequest(pairId, allowRetention) {
    const requestToken = token.value
    const res = await api.createBreakRequest(pairId, allowRetention)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function retainBreakRequest(pairId, requestId, message) {
    const requestToken = token.value
    const res = await api.retainBreakRequest(pairId, requestId, message)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function declineBreakRequest(pairId, requestId) {
    const requestToken = token.value
    const res = await api.declineBreakRequest(pairId, requestId)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function appendBreakRequestMessage(pairId, requestId, message) {
    const requestToken = token.value
    const res = await api.appendBreakRequestMessage(pairId, requestId, message)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function decideBreakRequestRetention(pairId, requestId, decision) {
    const requestToken = token.value
    const res = await api.decideBreakRequestRetention(pairId, requestId, decision)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function decidePairChangeRequest(pairId, requestId, decision) {
    const requestToken = token.value
    const res = await api.decidePairChangeRequest(pairId, requestId, decision)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function cancelPairChangeRequest(pairId, requestId) {
    const requestToken = token.value
    const res = await api.cancelPairChangeRequest(pairId, requestId)
    if (requestToken !== token.value) return null
    return syncPairBundle(res)
  }

  async function updatePartnerNickname(pairId, customNickname) {
    const normalizedNickname = String(customNickname || '').trim()
    if (token.value === DEMO_TOKEN) {
      const pair = pairs.value.find((item) => item.id === pairId)
      if (!pair) return null
      return upsertPair({
        ...pair,
        custom_partner_nickname: normalizedNickname || null,
      })
    }

    const requestToken = token.value
    const pair = await api.updatePartnerNickname(pairId, normalizedNickname)
    if (requestToken !== token.value) return null
    return upsertPair(pair)
  }

  async function bootstrap() {
    const requestToken = token.value
    if (!isLoggedIn.value) return false
    if (token.value === DEMO_TOKEN) {
      applyDemo()
      return true
    }
    try {
      await Promise.all([fetchMe(), fetchPairs(), loadNotifications()])
      return requestToken === token.value
    } catch {
      if (requestToken === token.value) logout()
      return false
    }
  }

  async function loadNotifications() {
    const requestToken = token.value
    if (token.value === DEMO_TOKEN) {
      notifications.value = cloneDemo(demoFixture.notifications)
      return
    }
    try {
      const result = await api.getNotifications()
      if (requestToken === token.value) notifications.value = result
    } catch {
      if (requestToken === token.value) notifications.value = []
    }
  }

  const unreadCount = computed(() =>
    notifications.value.filter((n) => !n.is_read).length
  )

  return {
    me, token, pairs, currentPair, notifications,
    isLoggedIn, isDemoMode, testingUnrestricted, hasActivePair, activePair, activePairId, currentPairId, partnerName, unreadCount,
    login, register, phoneLogin, logout,
    fetchMe, updateMe, fetchPairs, switchPair, createPair, previewJoinPair, joinPair, refreshPairInviteCode,
    refreshNicknameReferences,
    requestPairTypeChange, createBreakRequest, retainBreakRequest, declineBreakRequest,
    appendBreakRequestMessage, decideBreakRequestRetention, decidePairChangeRequest,
    cancelPairChangeRequest, updatePartnerNickname,
    bootstrap, loadNotifications, enterDemo,
  }
})

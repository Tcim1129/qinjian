import { defineStore } from 'pinia'
import { api } from '@/api'
import { ref } from 'vue'
import { createLatestRequest } from '@/utils/taskSchedule'
import { getAuthToken } from '@/utils/auth'

export const useCheckinStore = defineStore('checkin', () => {
  const streak = ref({})
  const todayStatus = ref({})
  const history = ref([])
  const requests = { streak: createLatestRequest(), today: createLatestRequest(), history: createLatestRequest() }

  async function loadScoped(key, target, read) {
    const current = requests[key].begin()
    const token = getAuthToken()
    const result = await read()
    if (current() && token === getAuthToken()) target.value = result
  }

  function reset() {
    Object.values(requests).forEach(request => request.invalidate())
    streak.value = {}
    todayStatus.value = {}
    history.value = []
  }

  async function loadStreak(pairId) {
    await loadScoped('streak', streak, () => api.getCheckinStreak(pairId))
  }

  async function loadTodayStatus(pairId) {
    await loadScoped('today', todayStatus, () => api.getTodayStatus(pairId))
  }

  async function loadHistory(pairId, limit = 14) {
    await loadScoped('history', history, () => api.getCheckinHistory(pairId, limit))
  }

  async function submit(pairId, payload) {
    return api.submitCheckin(pairId, payload)
  }

  return { streak, todayStatus, history, loadStreak, loadTodayStatus, loadHistory, submit, reset }
})

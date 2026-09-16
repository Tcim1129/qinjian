import { defineStore } from 'pinia'
import { api } from '@/api'
import { ref } from 'vue'
import { createLatestRequest } from '@/utils/taskSchedule'
import { getAuthToken } from '@/utils/auth'

export const useReportStore = defineStore('report', () => {
  const currentReport = ref(null)
  const reportHistory = ref([])
  const reportType = ref('daily')
  const latestLoads = createLatestRequest()
  const historyLoads = createLatestRequest()

  function reset() {
    latestLoads.invalidate()
    historyLoads.invalidate()
    currentReport.value = null
    reportHistory.value = []
    reportType.value = 'daily'
  }

  async function generate(pairId, type = 'daily') {
    reportType.value = type
    return api.generateReport(pairId, type)
  }

  async function loadLatest(pairId, type = 'daily') {
    const current = latestLoads.begin()
    const token = getAuthToken()
    reportType.value = type
    currentReport.value = null
    const result = await api.getLatestReport(pairId, type)
    if (!current() || token !== getAuthToken()) return null
    currentReport.value = result
    return currentReport.value
  }

  async function loadHistory(pairId, type = 'daily', limit = 7) {
    const current = historyLoads.begin()
    const token = getAuthToken()
    reportHistory.value = []
    const result = await api.getReportHistory(pairId, type, limit)
    if (!current() || token !== getAuthToken()) return []
    reportHistory.value = result
    return result
  }

  return { currentReport, reportHistory, reportType, generate, loadLatest, loadHistory, reset }
})

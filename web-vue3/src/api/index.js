import axios from 'axios'
import { shouldExpireSession } from '../utils/auth.js'
import { DEFAULT_API_TIMEOUT_MS, AI_INTERACTION_TIMEOUT_MS, normalizeApiErrorMessage } from '../utils/apiTimeouts.js'

let API_ROOT = '/api/v1'

function toWebSocketUrl(url) {
  const parsed = new URL(url, window.location.origin)
  parsed.protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
  return parsed.toString().replace(/\/$/, '')
}

const apiClient = axios.create({
  baseURL: API_ROOT,
  timeout: DEFAULT_API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('qj_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let unauthorizedHandler = null

apiClient.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const requestUrl = String(err.config?.url || '')
    const authorization = err.config?.headers?.get?.('Authorization') || err.config?.headers?.Authorization || ''
    const requestToken = String(authorization).replace(/^Bearer\s+/i, '')
    const currentToken = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('qj_token') : ''
    if (shouldExpireSession({ status, requestUrl, requestToken, currentToken })) {
      try {
        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.removeItem('qj_token')
        }
      } catch {
        // ignore storage errors
      }
      if (typeof unauthorizedHandler === 'function') {
        try {
          unauthorizedHandler()
        } catch {
          // ignore handler errors
        }
      }
    }
    const error = new Error(normalizeApiErrorMessage(err))
    error.status = error.statusCode = status
    error.code = err.code
    const retryAfter = err.response?.headers?.['retry-after']
    if (retryAfter != null) error.retryAfter = Number(retryAfter) || Math.max(0, Math.ceil((Date.parse(retryAfter) - Date.now()) / 1000))
    return Promise.reject(error)
  }
)

async function checkBackend() {
  try {
    await axios.get('/api/health', { timeout: 3000 })
    return true
  } catch {
    return false
  }
}

// —— 演示模式下的离线 mock：让 preview-demo 无需后端也能展示智能体协作 ——
function demoAgentMode() {
  try {
    return sessionStorage.getItem('qj_token') === 'demo-mode'
  } catch {
    return false
  }
}

function realAgentEnabled() {
  try {
    return (
      localStorage.getItem('qj_real_agent') !== '0' &&
      sessionStorage.getItem('qj_real_agent') !== '0'
    )
  } catch {
    return true
  }
}

function demoCheckupResult() {
  return {
    report:
      '本期主动巡查完成。关系健康分约 78/100，当前风险等级为“低风险（整体平稳）”。近期互动频率稳定、情绪多为正向，整体平稳。建议保持每周一次的深度对话，并留意异地期间的联系节奏。',
    health: 78,
    risk_level: 'low',
    risk_reason: '整体平稳，近 7 天无高冲突信号。',
    recommended_actions: [
      '周四安排一次 20 分钟深度通话',
      '记录一次对方近期最看重的事',
    ],
    urgency: 'monitor',
    generated_at: new Date().toISOString(),
  }
}

function demoSwarmResult(inputText) {
  const topic = String(inputText || '').trim() || '今天的心情与相处'
  return {
    reply:
      '我收到了，也陪你把这一段一起理了一遍。你更希望的是先被理解，而不是被马上给方案——那我们就不用赶，先聊聊今天具体发生了什么，我在听。',
    action: 'chat',
    swarm: [
      {
        role: 'perception',
        role_name: '感知',
        status: 'ok',
        summary: `已读取关系全景：健康分 78/100、近期 1 条新记录、无危机预警、2 项进行中任务。结合「${topic}」检索到这段关系整体平稳。`,
        duration_ms: 812,
      },
      {
        role: 'analysis',
        role_name: '分析',
        status: 'ok',
        summary: '判断当前为低强度情绪表达，无明显冲突升级信号，暂不需要强干预，适合走共情+澄清路线。',
        duration_ms: 640,
      },
      {
        role: 'action',
        role_name: '行动',
        status: 'ok',
        summary: '本轮暂不新建任务，维持现有 2 项行动节奏，观察后续互动。',
        duration_ms: 120,
      },
      {
        role: 'companion',
        role_name: '陪伴',
        status: 'ok',
        summary: '综合感知与分析简报，给出先理解、再澄清的陪伴式回应。',
        duration_ms: 520,
      },
    ],
    trace: [
      {
        step_index: 0,
        thought: '先了解这段关系现在的整体状态。',
        tool_calls: [{ function: { name: 'get_relationship_status', arguments: '{}' } }],
        tool_results: [{ name: 'get_relationship_status', result: { status: 'success', data: { health: 78 } } }],
        duration_ms: 812,
      },
    ],
  }
}

export function isRealAgentEnabled() {
  return realAgentEnabled()
}

const PHONE_VERIFICATION_ENABLED =
  import.meta.env?.VITE_PHONE_VERIFICATION_ENABLED === 'true'

function rejectDisabledPhoneVerification() {
  return Promise.reject(
    new Error('短信验证码功能暂未开放，请使用账号和密码登录')
  )
}

export const api = {
  checkBackend,

  login(account, password) {
    return apiClient.post('/auth/login', { account, password })
  },

  register(account, nickname, password) {
    return apiClient.post('/auth/register', { account, nickname, password })
  },

  sendPhoneCode(phone) {
    if (!PHONE_VERIFICATION_ENABLED) return rejectDisabledPhoneVerification()
    return apiClient.post('/auth/phone/send-code', { phone })
  },

  phoneLogin(phone, code) {
    if (!PHONE_VERIFICATION_ENABLED) return rejectDisabledPhoneVerification()
    return apiClient.post('/auth/phone/login', { phone, code })
  },

  resetPasswordByPhone(phone, code, newPassword) {
    if (!PHONE_VERIFICATION_ENABLED) return rejectDisabledPhoneVerification()
    return apiClient.post('/auth/password-reset/phone', {
      phone,
      code,
      new_password: newPassword,
    })
  },

  getMe() {
    return apiClient.get('/auth/me')
  },

  updateMe(payload) {
    return apiClient.put('/auth/me', payload)
  },

  changePassword(currentPassword, newPassword) {
    return apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  createPair(type) {
    return apiClient.post('/pairs/create', { type })
  },

  previewJoinPair(inviteCode) {
    return apiClient.post('/pairs/join/preview', { invite_code: inviteCode })
  },

  joinPair(inviteCode, type = 'couple') {
    return apiClient.post('/pairs/join', { invite_code: inviteCode, type })
  },

  refreshPairInviteCode(pairId) {
    return apiClient.post(`/pairs/${pairId}/invite-code/refresh`)
  },

  requestPairTypeChange(pairId, type) {
    return apiClient.patch(`/pairs/${pairId}/type`, { type })
  },

  getPairChangeRequest(pairId) {
    return apiClient.get(`/pairs/${pairId}/change-request`)
  },

  decidePairChangeRequest(pairId, requestId, decision) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/decision`, { decision })
  },

  cancelPairChangeRequest(pairId, requestId) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/cancel`)
  },

  createBreakRequest(pairId, allowRetention = true) {
    return apiClient.post(`/pairs/${pairId}/break-request`, { allow_retention: Boolean(allowRetention) })
  },

  retainBreakRequest(pairId, requestId, message) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/retain`, { message })
  },

  declineBreakRequest(pairId, requestId) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/decline-break`)
  },

  appendBreakRequestMessage(pairId, requestId, message) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/messages`, { message })
  },

  decideBreakRequestRetention(pairId, requestId, decision) {
    return apiClient.post(`/pairs/${pairId}/change-requests/${requestId}/retention-decision`, { decision })
  },

  getPairTaskSettings(pairId) {
    return apiClient.get(`/pairs/${pairId}/task-settings`)
  },

  updatePairTaskSettings(pairId, payload) {
    return apiClient.patch(`/pairs/${pairId}/task-settings`, payload)
  },

  getMyPairs() {
    return apiClient.get('/pairs/me')
  },

  getPairSummary() {
    return apiClient.get('/pairs/summary')
  },

  requestUnbind(pairId) {
    return apiClient.post(`/pairs/request-unbind?pair_id=${pairId}`)
  },

  confirmUnbind(pairId) {
    return apiClient.post(`/pairs/confirm-unbind?pair_id=${pairId}`)
  },

  cancelUnbind(pairId) {
    return apiClient.post(`/pairs/cancel-unbind?pair_id=${pairId}`)
  },

  updatePartnerNickname(pairId, customNickname) {
    return apiClient.post(`/pairs/${pairId}/partner-nickname`, { custom_nickname: customNickname })
  },

  submitCheckin(pairId, payload) {
    const url = pairId ? '/checkins/' : '/checkins/?mode=solo'
    return apiClient.post(url, pairId ? { pair_id: pairId, ...payload } : payload)
  },

  getTodayStatus(pairId, checkinDate = null) {
    const params = new URLSearchParams()
    if (pairId) params.set('pair_id', pairId)
    else params.set('mode', 'solo')
    if (checkinDate) params.set('checkin_date', checkinDate)
    return apiClient.get(`/checkins/today?${params.toString()}`)
  },

  previewCheckinSharing(recordId) {
    return apiClient.post('/mobile/checkins/sharing-preview', { record_id: recordId })
  },

  changeCheckinVisibility(recordId, visibilityScope, version) {
    return apiClient.patch(`/checkins/${recordId}/visibility`, {
      visibility_scope: visibilityScope, expected_version: String(version),
      sharing_confirmed: visibilityScope === 'shared_summary',
    })
  },

  getCheckinStreak(pairId) {
    const url = pairId ? `/checkins/streak?pair_id=${pairId}` : '/checkins/streak?mode=solo'
    return apiClient.get(url)
  },

  getCheckinHistory(pairId, limit = 14) {
    const url = pairId ? `/checkins/history?pair_id=${pairId}&limit=${limit}` : `/checkins/history?mode=solo&limit=${limit}`
    return apiClient.get(url)
  },

  generateReport(pairId, reportType = 'daily', reportDate = null) {
    const map = { daily: 'generate-daily', weekly: 'generate-weekly', monthly: 'generate-monthly' }
    const endpoint = map[reportType] || 'generate-daily'
    const params = new URLSearchParams()
    if (pairId) params.set('pair_id', pairId)
    else params.set('mode', 'solo')
    if (reportType === 'daily' && reportDate) params.set('report_date', reportDate)
    return apiClient.post(`/reports/${endpoint}?${params.toString()}`)
  },

  getLatestReport(pairId, reportType = 'daily') {
    const url = pairId ? `/reports/latest?pair_id=${pairId}&report_type=${reportType}` : `/reports/latest?mode=solo&report_type=${reportType}`
    return apiClient.get(url)
  },

  getReportHistory(pairId, reportType = 'daily', limit = 7) {
    const url = pairId ? `/reports/history?pair_id=${pairId}&report_type=${reportType}&limit=${limit}` : `/reports/history?mode=solo&report_type=${reportType}&limit=${limit}`
    return apiClient.get(url)
  },

  getReportTrend(pairId, days = 14) {
    const params = new URLSearchParams({ days: String(days) })
    if (pairId) params.set('pair_id', pairId)
    else params.set('mode', 'solo')
    return apiClient.get(`/reports/trend?${params.toString()}`)
  },

  getRelationshipTimeline(pairId, limit = 24) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (pairId) params.set('pair_id', pairId)
    else params.set('mode', 'solo')
    return apiClient.get(`/insights/timeline?${params.toString()}`)
  },

  getTimelineArchive(pairId, { before = null, limit = 60 } = {}) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (pairId) params.set('pair_id', pairId)
    else params.set('mode', 'solo')
    if (before) params.set('before', before)
    return apiClient.get(`/insights/timeline/archive?${params.toString()}`)
  },

  getTimelineEventDetail(eventId) {
    return apiClient.get(`/insights/timeline/events/${encodeURIComponent(eventId)}`)
  },

  getSafetyStatus(pairId) {
    const url = pairId ? `/insights/safety/status?pair_id=${pairId}` : '/insights/safety/status?mode=solo'
    return apiClient.get(url)
  },

  getMethodology(pairId) {
    const url = pairId ? `/insights/methodology?pair_id=${pairId}` : '/insights/methodology?mode=solo'
    return apiClient.get(url)
  },

  getTreeStatus(pairId) {
    return apiClient.get(`/tree/status?pair_id=${pairId}`)
  },

  waterTree(pairId) {
    return apiClient.post(`/tree/water?pair_id=${pairId}`)
  },

  collectTreeEnergy(pairId, nodeKey) {
    return apiClient.post('/tree/collect', { node_key: nodeKey }, { params: { pair_id: pairId } })
  },

  getCrisisStatus(pairId) {
    return apiClient.get(`/crisis/status/${pairId}`)
  },

  getDailyTasks(pairId, options = {}) {
    const params = new URLSearchParams()
    const forDate = options.forDate || options.for_date
    const dateScope = options.dateScope || options.date_scope || options.scope
    if (forDate) params.set('for_date', forDate)
    if (dateScope) params.set('date_scope', dateScope)
    const query = params.toString()
    return apiClient.get(`/tasks/daily/${pairId}${query ? `?${query}` : ''}`, { timeout: AI_INTERACTION_TIMEOUT_MS })
  },

  completeTask(taskId) {
    return apiClient.post(`/tasks/${taskId}/complete`)
  },
  reopenTask(taskId) {
    return apiClient.post(`/tasks/${taskId}/reopen`)
  },

  createManualTask(pairId, payload) {
    return apiClient.post(`/tasks/manual/${pairId}`, payload)
  },

  updateTask(taskId, payload) {
    return apiClient.patch(`/tasks/${taskId}`, payload)
  },

  refreshTask(taskId) {
    return apiClient.post(`/tasks/${taskId}/refresh`, {}, { timeout: AI_INTERACTION_TIMEOUT_MS })
  },

  submitTaskFeedback(taskId, payload) {
    return apiClient.post(`/tasks/${taskId}/feedback`, payload)
  },

  saveTaskResult(taskId, payload) {
    return apiClient.post(`/tasks/${taskId}/result`, payload)
  },

  getWeeklyAssessmentPack(pairId, options = {}) {
    const params = new URLSearchParams(pairId ? { pair_id: pairId } : { mode: 'solo' })
    const excludeIds = Array.isArray(options?.excludeItemIds)
      ? options.excludeItemIds.map((item) => String(item || '').trim()).filter(Boolean)
      : []
    if (excludeIds.length) {
      params.set('exclude_item_ids', excludeIds.join(','))
    }
    const variant = Number(options?.variant || 0)
    if (Number.isFinite(variant) && variant > 0) {
      params.set('variant', String(Math.floor(variant)))
    }
    return apiClient.get(`/insights/assessments/weekly-pack?${params.toString()}`)
  },

  submitWeeklyAssessment(pairId, payload) {
    const query = pairId ? `pair_id=${encodeURIComponent(pairId)}` : 'mode=solo'
    return apiClient.post(`/insights/assessments/weekly?${query}`, payload)
  },

  getLatestWeeklyAssessment(pairId) {
    const query = pairId ? `pair_id=${encodeURIComponent(pairId)}` : 'mode=solo'
    return apiClient.get(`/insights/assessments/latest?${query}`)
  },

  getWeeklyAssessmentTrend(pairId, limit = 4) {
    const query = new URLSearchParams(pairId ? { pair_id: pairId } : { mode: 'solo' })
    query.set('limit', String(limit))
    return apiClient.get(`/insights/assessments/trend?${query.toString()}`)
  },

  getMilestones(pairId) {
    return apiClient.get(`/milestones/${pairId}`)
  },

  createMilestone(pairId, milestoneType, title, milestoneDate) {
    return apiClient.post(`/milestones/?pair_id=${pairId}&milestone_type=${milestoneType}&title=${encodeURIComponent(title)}&milestone_date=${milestoneDate}`)
  },

  getLongDistanceHealth(pairId) {
    return apiClient.get(`/longdistance/health-index/${pairId}`)
  },

  getLongDistanceActivities(pairId, limit = 20) {
    return apiClient.get(`/longdistance/activities/${pairId}?limit=${limit}`)
  },

  createLongDistanceActivity(pairId, activityType, title = '') {
    const params = new URLSearchParams({ pair_id: pairId, activity_type: activityType })
    if (title) params.set('title', title)
    return apiClient.post(`/longdistance/activities?${params.toString()}`)
  },

  getAttachmentAnalysis(pairId) {
    if (!pairId) return apiClient.get('/tasks/attachment?mode=solo')
    return apiClient.get(`/tasks/attachment/${pairId}`)
  },

  triggerAttachmentAnalysis(pairId) {
    if (!pairId) {
      return apiClient.post(
        '/tasks/attachment/analyze?mode=solo',
        {},
        { timeout: AI_INTERACTION_TIMEOUT_MS }
      )
    }
    return apiClient.post(
      `/tasks/attachment/${pairId}/analyze`,
      {},
      { timeout: AI_INTERACTION_TIMEOUT_MS }
    )
  },

  getCommunityTips(pairType = 'couple', pairId = null) {
    const params = new URLSearchParams({ pair_type: pairType })
    if (pairId) params.set('pair_id', pairId)
    return apiClient.get(`/community/tips?${params.toString()}`)
  },

  generateTip(pairType = 'couple', pairId = null) {
    const params = new URLSearchParams({ pair_type: pairType })
    if (pairId) params.set('pair_id', pairId)
    return apiClient.post(`/community/tips/generate?${params.toString()}`)
  },

  getNotifications(limit = 20) {
    return apiClient.get(`/community/notifications?limit=${limit}`)
  },

  markNotificationRead(notificationId) {
    return apiClient.post(`/community/notifications/${encodeURIComponent(notificationId)}/read`)
  },

  markNotificationsRead() {
    return apiClient.post('/community/notifications/read-all')
  },

  createAgentSession(pairId = null, options = {}) {
    const params = new URLSearchParams()
    if (pairId) params.set('pair_id', pairId)
    if (options.force_new || options.forceNew) params.set('force_new', 'true')
    if (options.surface) params.set('surface', options.surface)
    const query = params.toString()
    return apiClient.post(`/agent/sessions${query ? `?${query}` : ''}`)
  },

  getAgentSessions(limit = 20) {
    return apiClient.get(`/agent/sessions?limit=${encodeURIComponent(limit)}`)
  },

  getAgentMessages(sessionId) {
    return apiClient.get(`/agent/sessions/${sessionId}/messages`)
  },

  chatWithAgent(sessionId, content) {
    const payload = content && typeof content === 'object' && !Array.isArray(content)
      ? content
      : { content }
    return apiClient.post(`/agent/sessions/${sessionId}/chat`, payload, { timeout: AI_INTERACTION_TIMEOUT_MS })
  },

  confirmAgentTask(sessionId, messageId, proposalId) {
    return apiClient.post(`/agent/sessions/${sessionId}/messages/${messageId}/tasks/${proposalId}/confirm`)
  },

  getAgentThoughts(sessionId) {
    return apiClient.get(`/agent/sessions/${sessionId}/thoughts`)
  },

  runAgentCheckup(sessionId) {
    if (demoAgentMode()) {
      return Promise.reject(new Error('登录账号后可以使用主动巡查。'))
    }
    return apiClient.post(`/agent/sessions/${sessionId}/checkup`)
  },

  collaborateWithAgent(sessionId, content) {
    if (demoAgentMode()) {
      return Promise.reject(new Error('登录账号后可以使用多视角分析。'))
    }
    const payload = content && typeof content === 'object' && !Array.isArray(content)
      ? content
      : { content }
    return apiClient.post(`/agent/sessions/${sessionId}/collaborate`, payload, { timeout: 160000 })
  },

  simulateMessage(pairId, draft) {
    const query = pairId ? `?pair_id=${encodeURIComponent(pairId)}` : ''
    return apiClient.post(`/agent/simulate-message${query}`, { draft }, { timeout: 60000 })
  },
  listExpressions(pairId) {
    return apiClient.get('/expressions', { params: pairId ? { pair_id: pairId } : {} })
  },
  saveExpression(id, payload) {
    return apiClient.put(`/expressions/${encodeURIComponent(id)}`, payload)
  },
  deleteExpression(id) {
    return apiClient.delete(`/expressions/${encodeURIComponent(id)}`)
  },

  submitDecisionFeedback(eventId, feedbackType, note = '') {
    return apiClient.post(`/agent/decision-feedback/${eventId}`, {
      feedback_type: feedbackType,
      note,
    })
  },

  getLatestNarrativeAlignment(pairId) {
    return apiClient.get(`/insights/alignment/latest?pair_id=${encodeURIComponent(pairId)}`)
  },

  generateNarrativeAlignment(pairId, options = {}) {
    const params = new URLSearchParams({ pair_id: pairId })
    if (options.force) params.set('force', 'true')
    return apiClient.post(`/insights/alignment/generate?${params.toString()}`, null, { timeout: 60000 })
  },

  getRepairProtocol(pairId = null) {
    const url = pairId ? `/crisis/protocol/${pairId}` : '/crisis/protocol?mode=solo'
    return apiClient.get(url)
  },

  getPrivacyStatus() {
    return apiClient.get('/privacy/status')
  },

  getPrivacyAudit(limit = 20) {
    return apiClient.get(`/privacy/audit/me?limit=${limit}`)
  },

  requestPrivacyDelete() {
    return apiClient.post('/privacy/delete-request')
  },

  cancelPrivacyDelete() {
    return apiClient.post('/privacy/delete-request/cancel')
  },

  async buildRealtimeAsrSocketUrl() {
    const token = sessionStorage.getItem('qj_token')
    if (!token) throw new Error('请先登录')
    if (token === 'demo-mode') throw new Error('预览模式不支持实时语音')
    const ticketRes = await apiClient.post('/agent/asr/ws-ticket')
    const ticket = String(ticketRes?.ticket || '').trim()
    if (!ticket) throw new Error('无法获取实时语音连接凭证')
    const absoluteApiRoot = API_ROOT.startsWith('http')
      ? API_ROOT
      : `${window.location.origin}${API_ROOT.startsWith('/') ? '' : '/'}${API_ROOT}`
    const socketUrl = new URL(`${toWebSocketUrl(absoluteApiRoot)}/agent/asr/realtime`)
    socketUrl.searchParams.set('ticket', ticket)
    return socketUrl.toString()
  },

  uploadFile(type, file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/upload/${type}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  analyzeImage(file, options = {}) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('context', options.context || '')
    formData.append('persist', options.persist ? 'true' : 'false')
    formData.append('privacy_mode', options.privacyMode || options.privacy_mode || 'cloud')
    return apiClient.post('/upload/image/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },

  transcribeVoice(file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/upload/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },

  isLoggedIn() {
    return Boolean(sessionStorage.getItem('qj_token'))
  },

  setToken(token) {
    if (token) sessionStorage.setItem('qj_token', token)
    else sessionStorage.removeItem('qj_token')
  },

  clearToken() {
    sessionStorage.removeItem('qj_token')
  },

  setUnauthorizedHandler(handler) {
    unauthorizedHandler = typeof handler === 'function' ? handler : null
  },
}

export default api

import defaultConfig from './config.example.js'

let localConfig = {}

try {
  const localModule = require('./config.local.js')
  localConfig = localModule.default || localModule
} catch (error) {
  localConfig = {}
}

const TOKEN_KEY = 'qj_app_token'
const USER_KEY = 'qj_app_user'
const PAIR_SUMMARY_KEY = 'qj_app_pair_summary'
const AUTH_REDIRECT_PATH = '/pages/auth/index'
const REQUEST_TIMEOUT = 15000
const MAX_READ_RETRIES = 1
const RETRYABLE_STATUS_CODES = [408, 429, 502, 503, 504]
const AUTH_ENDPOINTS = [
  '/auth/login',
  '/auth/register',
  '/auth/phone/login',
  '/auth/phone/send-code',
]

let volatileToken = ''
let legacyStorageCleared = false

function clearLegacySessionStorage() {
  if (legacyStorageCleared) return
  legacyStorageCleared = true
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
  uni.removeStorageSync(PAIR_SUMMARY_KEY)
}

function isAuthPath(path) {
  return AUTH_ENDPOINTS.some((item) => path.startsWith(item))
}

function extractErrorMessage(payload, fallback = '请求失败') {
  if (!payload) return fallback
  if (typeof payload === 'string') return payload
  return payload.detail || payload.message || payload.error || fallback
}

function createApiError({
  code = -1,
  message = '请求失败',
  data = null,
  detail = null,
  network = false,
  timeout = false,
  unauthorized = false,
} = {}) {
  const error = new Error(message)
  error.code = code
  error.data = data
  error.detail = detail
  error.network = network
  error.timeout = timeout
  error.unauthorized = unauthorized
  return error
}

function shouldRetry(method, error, attempt, retries) {
  if (attempt >= retries) return false
  if (method !== 'GET') return false
  if (!error) return false
  if (error.network || error.timeout) return true
  return RETRYABLE_STATUS_CODES.includes(error.code)
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function safeParseJson(raw) {
  if (!raw) return {}
  if (typeof raw !== 'string') return raw
  try {
    return JSON.parse(raw)
  } catch (error) {
    return raw
  }
}

class ApiClient {
  constructor() {
    const resolvedConfig = localConfig?.apiRoot ? localConfig : defaultConfig
    this.baseUrl = (resolvedConfig.apiRoot || '').replace(/\/$/, '')
    clearLegacySessionStorage()
    this.token = volatileToken
    this.lastUnauthorizedAt = 0
  }

  ensureBaseUrl() {
    if (!this.baseUrl) {
      throw createApiError({
        code: -2,
        message: '服务地址未配置，请检查 config.local.js',
      })
    }
    return this.baseUrl
  }

  setToken(token) {
    clearLegacySessionStorage()
    this.token = token || ''
    volatileToken = this.token
  }

  clearToken() {
    this.setToken('')
    clearLegacySessionStorage()
  }

  isLoggedIn() {
    return !!this.token
  }

  handleUnauthorized(path) {
    if (isAuthPath(path)) return
    const now = Date.now()
    if (now - this.lastUnauthorizedAt < 1200) return
    this.lastUnauthorizedAt = now
    this.clearToken()
    uni.reLaunch({
      url: AUTH_REDIRECT_PATH,
    })
  }

  async request(method, path, data = null, header = {}, options = {}) {
    const { retries = MAX_READ_RETRIES } = options
    const baseUrl = this.ensureBaseUrl()

    const attemptRequest = async (attempt = 0) => {
      try {
        return await new Promise((resolve, reject) => {
          uni.request({
            url: `${baseUrl}${path}`,
            method,
            data,
            timeout: REQUEST_TIMEOUT,
            header: {
              ...(data && method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
              ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
              ...header,
            },
            success: (res) => {
              if (res.statusCode >= 200 && res.statusCode < 300) {
                resolve(res.data)
                return
              }

              if (res.statusCode === 401) {
                this.handleUnauthorized(path)
                reject(createApiError({
                  code: 401,
                  message: '登录已失效，请重新登录',
                  data: res.data,
                  unauthorized: true,
                }))
                return
              }

              reject(createApiError({
                code: res.statusCode,
                message: extractErrorMessage(res.data, '请求失败'),
                data: res.data,
              }))
            },
            fail: (err) => {
              const isTimeout = String((err && err.errMsg) || '').toLowerCase().includes('timeout')
              reject(createApiError({
                code: isTimeout ? 408 : -1,
                message: isTimeout ? '请求超时，请稍后重试' : '网络连接失败，请检查网络后重试',
                detail: err,
                network: !isTimeout,
                timeout: isTimeout,
              }))
            },
          })
        })
      } catch (error) {
        if (shouldRetry(method, error, attempt, retries)) {
          await wait(250 * (attempt + 1))
          return attemptRequest(attempt + 1)
        }
        throw error
      }
    }

    return attemptRequest(0)
  }

  uploadFile(type, filePath) {
    const baseUrl = this.ensureBaseUrl()

    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${baseUrl}/upload/${type}`,
        filePath,
        name: 'file',
        timeout: REQUEST_TIMEOUT,
        header: this.token ? { Authorization: `Bearer ${this.token}` } : {},
        success: (res) => {
          const payload = safeParseJson(res.data)
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(payload)
            return
          }
          if (res.statusCode === 401) {
            this.handleUnauthorized(`/upload/${type}`)
            reject(createApiError({
              code: 401,
              message: '登录已失效，请重新登录',
              data: payload,
              unauthorized: true,
            }))
            return
          }
          reject(createApiError({
            code: res.statusCode,
            message: extractErrorMessage(payload, '上传失败'),
            data: payload,
          }))
        },
        fail: (err) => {
          const isTimeout = String((err && err.errMsg) || '').toLowerCase().includes('timeout')
          reject(createApiError({
            code: isTimeout ? 408 : -1,
            message: isTimeout ? '上传超时，请稍后重试' : '上传失败，请检查网络后重试',
            detail: err,
            network: !isTimeout,
            timeout: isTimeout,
          }))
        },
      })
    })
  }

  login(email, password) {
    return this.request('POST', '/auth/login', { email, password }).then((payload) => {
      this.setToken(payload.access_token)
      return payload
    })
  }

  register(email, nickname, password) {
    return this.request('POST', '/auth/register', { email, nickname, password }).then((payload) => {
      this.setToken(payload.access_token)
      return payload
    })
  }

  phoneLogin(phone, code) {
    return this.request('POST', '/auth/phone/login', { phone, code }).then((payload) => {
      this.setToken(payload.access_token)
      return payload
    })
  }

  sendPhoneCode(phone) { return this.request('POST', '/auth/phone/send-code', { phone }) }
  getMe() { return this.request('GET', '/auth/me') }
  updateMe(payload) { return this.request('PUT', '/auth/me', payload) }
  changePassword(currentPassword, newPassword) { return this.request('POST', '/auth/change-password', { current_password: currentPassword, new_password: newPassword }) }
  getPairSummary() { return this.request('GET', '/pairs/summary') }
  getMyPairs() { return this.request('GET', '/pairs/me') }
  createPair(type) { return this.request('POST', '/pairs/create', { type }) }
  joinPair(inviteCode) { return this.request('POST', '/pairs/join', { invite_code: inviteCode }) }
  updatePartnerNickname(pairId, customNickname) { return this.request('POST', `/pairs/${pairId}/partner-nickname`, { custom_nickname: customNickname }) }
  requestUnbind(pairId) { return this.request('POST', `/pairs/request-unbind?pair_id=${pairId}`) }
  confirmUnbind(pairId) { return this.request('POST', `/pairs/confirm-unbind?pair_id=${pairId}`) }
  cancelUnbind(pairId) { return this.request('POST', `/pairs/cancel-unbind?pair_id=${pairId}`) }
  getUnbindStatus(pairId) { return this.request('GET', `/pairs/unbind-status?pair_id=${pairId}`) }
  submitCheckin(payload, mode = '') { return this.request('POST', `/checkins/${mode ? `?mode=${mode}` : ''}`, payload) }
  getTodayStatus(pairId = null) { return this.request('GET', pairId ? `/checkins/today?pair_id=${pairId}` : '/checkins/today?mode=solo') }
  getCheckinStreak(pairId = null) { return this.request('GET', pairId ? `/checkins/streak?pair_id=${pairId}` : '/checkins/streak?mode=solo') }
  getTreeStatus(pairId) { return this.request('GET', `/tree/status?pair_id=${pairId}`) }
  getLatestReport(pairId = null, reportType = 'daily') {
    return this.request('GET', pairId ? `/reports/latest?pair_id=${pairId}&report_type=${reportType}` : `/reports/latest?mode=solo&report_type=${reportType}`)
  }
  getReportHistory(pairId = null, reportType = 'daily', limit = 7) {
    return this.request('GET', pairId ? `/reports/history?pair_id=${pairId}&report_type=${reportType}&limit=${limit}` : `/reports/history?mode=solo&report_type=${reportType}&limit=${limit}`)
  }
  getHealthTrend(pairId = null, days = 14) {
    return this.request('GET', pairId ? `/reports/trend?pair_id=${pairId}&days=${days}` : `/reports/trend?mode=solo&days=${days}`)
  }
  getSafetyStatus(pairId = null) {
    return this.request('GET', pairId ? `/insights/safety/status?pair_id=${pairId}` : '/insights/safety/status?mode=solo')
  }
  submitWeeklyAssessment(pairId = null, payload = {}) {
    return this.request('POST', pairId ? `/insights/assessments/weekly?pair_id=${pairId}` : '/insights/assessments/weekly?mode=solo', payload)
  }
  getWeeklyAssessmentLatest(pairId = null) {
    return this.request('GET', pairId ? `/insights/assessments/latest?pair_id=${pairId}` : '/insights/assessments/latest?mode=solo')
  }
  getWeeklyAssessmentTrend(pairId = null, limit = 4) {
    return this.request('GET', pairId ? `/insights/assessments/trend?pair_id=${pairId}&limit=${limit}` : `/insights/assessments/trend?mode=solo&limit=${limit}`)
  }
  getPolicyDecisionAudit(pairId = null) {
    return this.request('GET', pairId ? `/insights/plans/policy-audit?pair_id=${pairId}` : '/insights/plans/policy-audit?mode=solo')
  }
  getPrivacyStatus() {
    return this.request('GET', '/privacy/status')
  }
  createPrivacyDeleteRequest() {
    return this.request('POST', '/privacy/delete-request')
  }
  cancelPrivacyDeleteRequest() {
    return this.request('POST', '/privacy/delete-request/cancel')
  }
  generateDailyReport(pairId = null) { return this.request('POST', pairId ? `/reports/generate-daily?pair_id=${pairId}` : '/reports/generate-daily?mode=solo') }
  generateWeeklyReport(pairId) { return this.request('POST', `/reports/generate-weekly?pair_id=${pairId}`) }
  generateMonthlyReport(pairId) { return this.request('POST', `/reports/generate-monthly?pair_id=${pairId}`) }
  createAgentSession(pairId = null) { return this.request('POST', `/agent/sessions${pairId ? `?pair_id=${pairId}` : ''}`) }
  getAgentMessages(sessionId) { return this.request('GET', `/agent/sessions/${sessionId}/messages`) }
  chatWithAgent(sessionId, content) { return this.request('POST', `/agent/sessions/${sessionId}/chat`, { content }) }
}

const api = new ApiClient()

export default api

import defaultConfig from './config.example.js'

let localConfig = {}

try {
  const localModule = require('./config.local.js')
  localConfig = localModule.default || localModule
} catch (error) {
  localConfig = {}
}

const TOKEN_KEY = 'qj_app_token'

class ApiClient {
  constructor() {
    const resolvedConfig = localConfig?.apiRoot ? localConfig : defaultConfig
    this.baseUrl = (resolvedConfig.apiRoot || '').replace(/\/$/, '')
    this.token = uni.getStorageSync(TOKEN_KEY) || ''
  }

  setToken(token) {
    this.token = token || ''
    if (this.token) {
      uni.setStorageSync(TOKEN_KEY, this.token)
    } else {
      uni.removeStorageSync(TOKEN_KEY)
    }
  }

  clearToken() {
    this.setToken('')
  }

  isLoggedIn() {
    return !!this.token
  }

  request(method, path, data = null, header = {}) {
    return new Promise((resolve, reject) => {
      uni.request({
        url: `${this.baseUrl}${path}`,
        method,
        data,
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
            this.clearToken()
          }
          reject(new Error(res.data?.detail || res.data?.message || '请求失败'))
        },
        fail: () => reject(new Error('网络连接失败')),
      })
    })
  }

  uploadFile(type, filePath) {
    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${this.baseUrl}/upload/${type}`,
        filePath,
        name: 'file',
        header: this.token ? { Authorization: `Bearer ${this.token}` } : {},
        success: (res) => {
          const payload = JSON.parse(res.data || '{}')
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(payload)
            return
          }
          reject(new Error(payload.detail || payload.message || '上传失败'))
        },
        fail: () => reject(new Error('上传失败')),
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
  generateDailyReport(pairId = null) { return this.request('POST', pairId ? `/reports/generate-daily?pair_id=${pairId}` : '/reports/generate-daily?mode=solo') }
  generateWeeklyReport(pairId) { return this.request('POST', `/reports/generate-weekly?pair_id=${pairId}`) }
  generateMonthlyReport(pairId) { return this.request('POST', `/reports/generate-monthly?pair_id=${pairId}`) }
  createAgentSession(pairId = null) { return this.request('POST', `/agent/sessions${pairId ? `?pair_id=${pairId}` : ''}`) }
  getAgentMessages(sessionId) { return this.request('GET', `/agent/sessions/${sessionId}/messages`) }
  chatWithAgent(sessionId, content) { return this.request('POST', `/agent/sessions/${sessionId}/chat`, { content }) }
}

const api = new ApiClient()

export default api

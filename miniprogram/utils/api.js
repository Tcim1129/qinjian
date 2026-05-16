/**
 * Miniprogram API client
 * Focused on production basics: timeout, retry, error normalization, and auth expiry handling.
 */

const API_PREFIX = '/api/v1'
const REQUEST_TIMEOUT = 15000
const MAX_READ_RETRIES = 1
const RETRYABLE_STATUS_CODES = [408, 429, 502, 503, 504]
const OPTIONAL_ENDPOINT_PREFIXES = [
  '/insights/safety/status',
  '/insights/assessments/latest',
  '/insights/assessments/trend',
  '/insights/plans/policy-audit',
]

let unauthorizedPending = false
const unsupportedOptionalEndpoints = new Set()

function getGlobalData() {
  const app = getApp()
  return app ? app.globalData : {}
}

function isAuthEndpoint(url) {
  return url === '/auth/login' || url === '/auth/phone/login' || url === '/auth/register'
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

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function shouldRetry(method, error, attempt, retries) {
  if (attempt >= retries) return false
  if (method !== 'GET') return false
  if (!error) return false
  if (error.network || error.timeout) return true
  return RETRYABLE_STATUS_CODES.includes(error.code)
}

function showNetworkToast(message) {
  wx.showToast({
    title: message,
    icon: 'none',
    duration: 2200,
  })
}

function handleUnauthorized() {
  if (unauthorizedPending) return
  unauthorizedPending = true

  const app = getApp()
  if (app && app.globalData) {
    app.globalData.token = null
    app.globalData.userInfo = null
    app.globalData.pairInfo = null
    app.globalData.isLoggedIn = false
  }

  wx.removeStorageSync('token')
  wx.removeStorageSync('userInfo')
  wx.removeStorageSync('pairInfo')

  wx.reLaunch({
    url: '/pages/login/login',
  })

  setTimeout(() => {
    unauthorizedPending = false
  }, 1200)
}

function ensureBaseUrl() {
  const globalData = getGlobalData()
  const baseUrl = globalData.baseUrl || ''
  if (!baseUrl) {
    throw createApiError({
      code: -2,
      message: '服务地址未配置，请先完成环境配置',
    })
  }
  return baseUrl
}

function getOptionalEndpointPrefix(url) {
  return OPTIONAL_ENDPOINT_PREFIXES.find((prefix) => url.startsWith(prefix)) || null
}

function shouldSkipOptionalEndpoint(url) {
  const prefix = getOptionalEndpointPrefix(url)
  return prefix ? unsupportedOptionalEndpoints.has(prefix) : false
}

function markOptionalEndpointUnsupported(url, error) {
  const prefix = getOptionalEndpointPrefix(url)
  if (!prefix || !error) return
  if (error.code === 404 || error.code === 501) {
    unsupportedOptionalEndpoints.add(prefix)
  }
}

async function request(url, method, data, options = {}) {
  const { retries = MAX_READ_RETRIES, silent = false } = options

  const attemptRequest = async (attempt = 0) => {
    const globalData = getGlobalData()
    const baseUrl = ensureBaseUrl()
    const token = globalData.token || ''
    const header = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }

    try {
      return await new Promise((resolve, reject) => {
        wx.request({
          url: `${baseUrl}${API_PREFIX}${url}`,
          method,
          data,
          header,
          timeout: REQUEST_TIMEOUT,
          success(res) {
            if (res.statusCode === 401 && !isAuthEndpoint(url)) {
              handleUnauthorized()
              reject(createApiError({
                code: 401,
                message: '登录已失效，请重新登录',
                data: res.data,
                unauthorized: true,
              }))
              return
            }

            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(res.data)
              return
            }

            reject(createApiError({
              code: res.statusCode,
              message: extractErrorMessage(res.data, '请求失败'),
              data: res.data,
            }))
          },
          fail(err) {
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

      if (!silent && (error.network || error.timeout)) {
        showNetworkToast(error.message)
      }
      throw error
    }
  }

  return attemptRequest(0)
}

function get(url, data, options) {
  return request(url, 'GET', data, options)
}

function post(url, data, options) {
  return request(url, 'POST', data, options)
}

function put(url, data, options) {
  return request(url, 'PUT', data, options)
}

function del(url, data, options) {
  return request(url, 'DELETE', data, options)
}

async function getOptional(url, data, options) {
  if (shouldSkipOptionalEndpoint(url)) {
    return null
  }

  try {
    return await get(url, data, { ...(options || {}), silent: true })
  } catch (error) {
    markOptionalEndpointUnsupported(url, error)
    if (error && (error.code === 404 || error.code === 501)) {
      return null
    }
    throw error
  }
}

function safeParseUploadPayload(raw) {
  if (!raw) return {}
  if (typeof raw !== 'string') return raw
  try {
    return JSON.parse(raw)
  } catch (error) {
    return raw
  }
}

function upload(url, filePath, formData) {
  return new Promise((resolve, reject) => {
    let baseUrl = ''
    try {
      baseUrl = ensureBaseUrl()
    } catch (error) {
      reject(error)
      return
    }

    const globalData = getGlobalData()
    const token = globalData.token || ''
    const header = token ? { Authorization: `Bearer ${token}` } : {}

    wx.uploadFile({
      url: `${baseUrl}${API_PREFIX}${url}`,
      filePath,
      name: 'file',
      header,
      formData: formData || {},
      timeout: REQUEST_TIMEOUT,
      success(res) {
        if (res.statusCode === 401 && !isAuthEndpoint(url)) {
          handleUnauthorized()
          reject(createApiError({
            code: 401,
            message: '登录已失效，请重新登录',
            unauthorized: true,
          }))
          return
        }

        const payload = safeParseUploadPayload(res.data)
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(payload)
          return
        }

        reject(createApiError({
          code: res.statusCode,
          message: extractErrorMessage(payload, '上传失败'),
          data: payload,
        }))
      },
      fail(err) {
        const isTimeout = String((err && err.errMsg) || '').toLowerCase().includes('timeout')
        const error = createApiError({
          code: isTimeout ? 408 : -1,
          message: isTimeout ? '上传超时，请稍后重试' : '网络连接失败，请检查网络后重试',
          detail: err,
          network: !isTimeout,
          timeout: isTimeout,
        })
        showNetworkToast(error.message)
        reject(error)
      },
    })
  })
}

function getBaseApiUrl() {
  const baseUrl = ensureBaseUrl()
  return `${baseUrl}${API_PREFIX}`
}

function toWebSocketUrl(url) {
  const value = String(url || '').trim()
  if (!value) return ''
  if (value.startsWith('https://')) return `wss://${value.slice(8)}`
  if (value.startsWith('http://')) return `ws://${value.slice(7)}`
  return value
}

function getRealtimeAsrSocketUrl() {
  const baseUrl = ensureBaseUrl()
  const globalData = getGlobalData()
  const token = globalData.token || ''
  if (!token) {
    throw createApiError({
      code: 401,
      message: '登录已失效，请重新登录',
      unauthorized: true,
    })
  }

  const socketUrl = `${toWebSocketUrl(baseUrl)}${API_PREFIX}/agent/asr/realtime?token=${encodeURIComponent(token)}`
  return socketUrl
}

function uploadAndTranscribe(filePath) {
  return new Promise((resolve, reject) => {
    let baseUrl = ''
    try {
      baseUrl = ensureBaseUrl()
    } catch (error) {
      reject(error)
      return
    }

    const globalData = getGlobalData()
    const token = globalData.token || ''
    const header = token ? { Authorization: `Bearer ${token}` } : {}

    wx.uploadFile({
      url: `${baseUrl}${API_PREFIX}/upload/transcribe`,
      filePath,
      name: 'file',
      header,
      timeout: REQUEST_TIMEOUT,
      success(res) {
        if (res.statusCode === 401) {
          handleUnauthorized()
          reject(createApiError({
            code: 401,
            message: '登录已失效，请重新登录',
            unauthorized: true,
          }))
          return
        }

        const payload = safeParseUploadPayload(res.data)
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(payload)
          return
        }

        reject(createApiError({
          code: res.statusCode,
          message: extractErrorMessage(payload, '转录失败'),
          data: payload,
        }))
      },
      fail(err) {
        const isTimeout = String((err && err.errMsg) || '').toLowerCase().includes('timeout')
        const error = createApiError({
          code: isTimeout ? 408 : -1,
          message: isTimeout ? '转录超时，请稍后重试' : '网络连接失败，请检查网络后重试',
          detail: err,
          network: !isTimeout,
          timeout: isTimeout,
        })
        showNetworkToast(error.message)
        reject(error)
      },
    })
  })
}

module.exports = {
  get,
  post,
  put,
  del,
  upload,
  uploadAndTranscribe,
  getBaseApiUrl,
  getRealtimeAsrSocketUrl,
  getSafetyStatus(pairId) {
    return getOptional(pairId ? `/insights/safety/status?pair_id=${pairId}` : '/insights/safety/status?mode=solo')
  },
  submitWeeklyAssessment(pairId, payload) {
    return post(pairId ? `/insights/assessments/weekly?pair_id=${pairId}` : '/insights/assessments/weekly?mode=solo', payload)
  },
  getWeeklyAssessmentLatest(pairId) {
    return getOptional(pairId ? `/insights/assessments/latest?pair_id=${pairId}` : '/insights/assessments/latest?mode=solo')
  },
  getWeeklyAssessmentTrend(pairId, limit = 4) {
    return getOptional(pairId ? `/insights/assessments/trend?pair_id=${pairId}&limit=${limit}` : `/insights/assessments/trend?mode=solo&limit=${limit}`)
  },
  getPolicyDecisionAudit(pairId) {
    return getOptional(pairId ? `/insights/plans/policy-audit?pair_id=${pairId}` : '/insights/plans/policy-audit?mode=solo')
  },
  getPrivacyStatus() {
    return getOptional('/privacy/status')
  },
  createPrivacyDeleteRequest() {
    return post('/privacy/delete-request')
  },
  cancelPrivacyDeleteRequest() {
    return post('/privacy/delete-request/cancel')
  },
}

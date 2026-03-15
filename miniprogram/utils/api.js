/**
 * API 请求封装模块
 * 基于 wx.request 的统一网络请求工具
 */

const API_PREFIX = '/api/v1'

/**
 * 获取应用全局数据
 */
function getGlobalData() {
  const app = getApp()
  return app ? app.globalData : {}
}

function isAuthEndpoint(url) {
  return url === '/auth/login' || url === '/auth/phone/login' || url === '/auth/register'
}

/**
 * 处理 401 未授权响应
 * 清除登录态并跳转到登录页
 */
function handleUnauthorized() {
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
    url: '/pages/login/login'
  })
}

/**
 * 核心请求方法
 * @param {string} url - 请求路径（不含 baseUrl 和前缀）
 * @param {string} method - HTTP 方法
 * @param {object} data - 请求数据
 * @returns {Promise}
 */
function request(url, method, data) {
  return new Promise((resolve, reject) => {
    const globalData = getGlobalData()
    const baseUrl = globalData.baseUrl || ''
    const token = globalData.token || ''

    const header = {
      'Content-Type': 'application/json'
    }

    // 存在 token 时添加认证头
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    wx.request({
      url: `${baseUrl}${API_PREFIX}${url}`,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode === 401 && !isAuthEndpoint(url)) {
          handleUnauthorized()
          reject({ code: 401, message: '登录已过期，请重新登录' })
          return
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const errMsg = (res.data && (res.data.detail || res.data.message)) || '请求失败'
          reject({ code: res.statusCode, message: errMsg, data: res.data })
        }
      },
      fail(err) {
        wx.showToast({
          title: '网络连接失败，请检查网络设置',
          icon: 'none',
          duration: 2000
        })
        reject({ code: -1, message: '网络异常', detail: err })
      }
    })
  })
}

/**
 * GET 请求
 * @param {string} url - 请求路径
 * @param {object} [data] - 查询参数
 */
function get(url, data) {
  return request(url, 'GET', data)
}

/**
 * POST 请求
 * @param {string} url - 请求路径
 * @param {object} [data] - 请求体数据
 */
function post(url, data) {
  return request(url, 'POST', data)
}

/**
 * PUT 请求
 * @param {string} url - 请求路径
 * @param {object} [data] - 请求体数据
 */
function put(url, data) {
  return request(url, 'PUT', data)
}

/**
 * DELETE 请求
 * @param {string} url - 请求路径
 * @param {object} [data] - 请求体数据
 */
function del(url, data) {
  return request(url, 'DELETE', data)
}

/**
 * 文件上传
 * @param {string} url - 上传接口路径
 * @param {string} filePath - 本地文件路径
 * @param {object} [formData] - 附加表单数据
 * @returns {Promise}
 */
function upload(url, filePath, formData) {
  return new Promise((resolve, reject) => {
    const globalData = getGlobalData()
    const baseUrl = globalData.baseUrl || ''
    const token = globalData.token || ''

    const header = {}

    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    wx.uploadFile({
      url: `${baseUrl}${API_PREFIX}${url}`,
      filePath,
      name: 'file',
      header,
      formData: formData || {},
      success(res) {
        if (res.statusCode === 401 && !isAuthEndpoint(url)) {
          handleUnauthorized()
          reject({ code: 401, message: '登录已过期，请重新登录' })
          return
        }

        // wx.uploadFile 的 res.data 是字符串，需要解析
        let data = res.data
        try {
          data = JSON.parse(data)
        } catch (e) {
          // 解析失败则保留原始字符串
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data)
        } else {
          const errMsg = (data && data.message) || '上传失败'
          reject({ code: res.statusCode, message: errMsg, data })
        }
      },
      fail(err) {
        wx.showToast({
          title: '网络连接失败，请检查网络设置',
          icon: 'none',
          duration: 2000
        })
        reject({ code: -1, message: '网络异常', detail: err })
      }
    })
  })
}

function getBaseApiUrl() {
  const globalData = getGlobalData()
  const baseUrl = globalData.baseUrl || ''
  return `${baseUrl}${API_PREFIX}`
}

/**
 * 上传语音文件并转录为文字
 * @param {string} filePath - 本地语音文件路径
 * @returns {Promise<{text: string, size: number}>}
 */
function uploadAndTranscribe(filePath) {
  return new Promise((resolve, reject) => {
    const globalData = getGlobalData()
    const baseUrl = globalData.baseUrl || ''
    const token = globalData.token || ''

    const header = {}
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    wx.uploadFile({
      url: `${baseUrl}${API_PREFIX}/upload/transcribe`,
      filePath,
      name: 'file',
      header,
      success(res) {
        if (res.statusCode === 401) {
          handleUnauthorized()
          reject({ code: 401, message: '登录已过期，请重新登录' })
          return
        }

        let data = res.data
        try {
          data = JSON.parse(data)
        } catch (e) {
          // 解析失败则保留原始字符串
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data)
        } else {
          const errMsg = (data && data.detail) || data.message || '转录失败'
          reject({ code: res.statusCode, message: errMsg, data })
        }
      },
      fail(err) {
        wx.showToast({
          title: '网络连接失败，请检查网络设置',
          icon: 'none',
          duration: 2000
        })
        reject({ code: -1, message: '网络异常', detail: err })
      }
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
  getBaseApiUrl
}

import config from './config'

export function request(options) {
  const token = uni.getStorageSync('token')

  return new Promise((resolve, reject) => {
    uni.request({
      url: config.apiBaseUrl + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const detail = res.data && (res.data.detail || res.data.message)
          const message = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : `请求失败 (${res.statusCode})`)
          const err = new Error(message)
          err.statusCode = res.statusCode
          err.data = res.data
          reject(err)
        }
      },
      fail: (err) => {
        const error = new Error(err.errMsg || '网络连接异常，请检查服务地址')
        error.raw = err
        reject(error)
      }
    })
  })
}

export function get(url, data) {
  return request({ url, method: 'GET', data })
}

export function post(url, data) {
  return request({ url, method: 'POST', data })
}

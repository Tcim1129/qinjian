import { getRouteStack, popRoute, pushRoute, relaunchRoute } from './route-state.js'

function emitRecorderError(handlers, error) {
  handlers.forEach((handler) => {
    try {
      handler({ errMsg: error?.message || 'record:fail' })
    } catch (_) {
      // ignore
    }
  })
}

function createBrowserRecorderManager() {
  const stopHandlers = []
  const errorHandlers = []
  let mediaRecorder = null
  let mediaStream = null
  let chunks = []
  let autoStopTimer = null

  function cleanupStream() {
    if (autoStopTimer) {
      window.clearTimeout(autoStopTimer)
      autoStopTimer = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop())
      mediaStream = null
    }
  }

  function notifyStop() {
    const mimeType = mediaRecorder?.mimeType || 'audio/webm'
    const blob = chunks.length ? new Blob(chunks, { type: mimeType }) : null
    const file = blob
      ? new File([blob], `qinjian-recording-${Date.now()}.webm`, { type: mimeType })
      : null

    stopHandlers.forEach((handler) => {
      try {
        handler({
          tempFilePath: file,
          file,
          size: blob?.size || 0,
        })
      } catch (_) {
        // ignore
      }
    })
  }

  return {
    onStop(handler) {
      if (typeof handler === 'function') {
        stopHandlers.push(handler)
      }
    },
    onError(handler) {
      if (typeof handler === 'function') {
        errorHandlers.push(handler)
      }
    },
    async start(options = {}) {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        const unsupportedError = new Error('当前浏览器不支持录音')
        emitRecorderError(errorHandlers, unsupportedError)
        throw unsupportedError
      }

      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaRecorder = new MediaRecorder(mediaStream)
        chunks = []

        mediaRecorder.ondataavailable = (event) => {
          if (event.data?.size) {
            chunks.push(event.data)
          }
        }

        mediaRecorder.onerror = (event) => {
          cleanupStream()
          emitRecorderError(errorHandlers, event.error || new Error('录音失败'))
        }

        mediaRecorder.onstop = () => {
          notifyStop()
          cleanupStream()
        }

        mediaRecorder.start()

        const duration = Math.max(0, Number(options.duration) || 0)
        if (duration > 0) {
          autoStopTimer = window.setTimeout(() => {
            this.stop()
          }, duration)
        }
        return true
      } catch (error) {
        cleanupStream()
        emitRecorderError(errorHandlers, error)
        throw error
      }
    },
    stop() {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop()
        return
      }
      cleanupStream()
    },
  }
}

function ensureToastHost() {
  let host = document.getElementById('qj-web-toast-host')
  if (host) return host
  host = document.createElement('div')
  host.id = 'qj-web-toast-host'
  host.style.position = 'fixed'
  host.style.left = '50%'
  host.style.bottom = '96px'
  host.style.transform = 'translateX(-50%)'
  host.style.zIndex = '9999'
  host.style.display = 'flex'
  host.style.flexDirection = 'column'
  host.style.alignItems = 'center'
  host.style.gap = '10px'
  host.style.pointerEvents = 'none'
  document.body.appendChild(host)
  return host
}

function showToast(options = {}) {
  const title = options.title || '已处理'
  const host = ensureToastHost()
  const toast = document.createElement('div')
  toast.textContent = title
  toast.style.maxWidth = 'min(88vw, 420px)'
  toast.style.padding = '12px 18px'
  toast.style.borderRadius = '999px'
  toast.style.background = 'rgba(47, 37, 34, 0.92)'
  toast.style.color = '#fff'
  toast.style.fontSize = '14px'
  toast.style.fontWeight = '600'
  toast.style.boxShadow = '0 12px 28px rgba(47, 37, 34, 0.24)'
  toast.style.opacity = '0'
  toast.style.transition = 'opacity 160ms ease, transform 160ms ease'
  toast.style.transform = 'translateY(8px)'
  host.appendChild(toast)
  requestAnimationFrame(() => {
    toast.style.opacity = '1'
    toast.style.transform = 'translateY(0)'
  })
  window.setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transform = 'translateY(8px)'
    window.setTimeout(() => toast.remove(), 180)
  }, 1800)
}

function storageGet(key) {
  try {
    return window.localStorage.getItem(key)
  } catch (_) {
    return null
  }
}

function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch (_) {
    // ignore
  }
}

function storageRemove(key) {
  try {
    window.localStorage.removeItem(key)
  } catch (_) {
    // ignore
  }
}

async function request(options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeout || 15000)
  try {
    const response = await fetch(options.url, {
      method: options.method || 'GET',
      headers: options.header || {},
      body:
        options.data && options.method && options.method.toUpperCase() !== 'GET'
          ? typeof options.data === 'string' || options.data instanceof FormData
            ? options.data
            : JSON.stringify(options.data)
          : undefined,
      signal: controller.signal,
      credentials: 'same-origin',
    })
    const rawText = await response.text()
    let parsed = rawText
    try {
      parsed = rawText ? JSON.parse(rawText) : {}
    } catch (_) {
      parsed = rawText
    }
    options.success?.({
      statusCode: response.status,
      data: parsed,
    })
  } catch (error) {
    options.fail?.({
      errMsg: error?.name === 'AbortError' ? 'request:fail timeout' : `request:fail ${error?.message || 'network error'}`,
    })
  } finally {
    window.clearTimeout(timeout)
  }
}

async function uploadFile(options = {}) {
  if (!options.filePath || typeof options.filePath === 'string') {
    options.fail?.({ errMsg: 'uploadFile:fail browser file path unsupported' })
    return
  }

  const formData = new FormData()
  formData.append(options.name || 'file', options.filePath)
  const response = await fetch(options.url, {
    method: 'POST',
    body: formData,
    headers: options.header || {},
    credentials: 'same-origin',
  })
  const rawText = await response.text()
  options.success?.({
    statusCode: response.status,
    data: rawText,
  })
}

export function installWebUni() {
  globalThis.__QJ_API_ROOT__ = `${window.location.origin}/api/v1`
  globalThis.getCurrentPages = () => getRouteStack().map((route) => ({
    route: route.replace(/^\//, ''),
  }))

  const browserRecorderManager = createBrowserRecorderManager()

  globalThis.uni = {
    request,
    uploadFile,
    showToast,
    showModal(options = {}) {
      const ok = window.confirm([options.title, options.content].filter(Boolean).join('\n\n'))
      options.success?.({
        confirm: ok,
        cancel: !ok,
      })
    },
    reLaunch(options = {}) {
      relaunchRoute(options.url || '/pages/index/index')
      options.success?.()
    },
    navigateTo(options = {}) {
      pushRoute(options.url || '/pages/index/index')
      options.success?.()
    },
    navigateBack(options = {}) {
      popRoute(options.delta || 1)
      options.success?.()
    },
    setStorageSync(key, value) {
      storageSet(key, value)
    },
    getStorageSync(key) {
      return storageGet(key)
    },
    removeStorageSync(key) {
      storageRemove(key)
    },
    getRecorderManager() {
      return browserRecorderManager
    },
  }
}

export const DEFAULT_API_TIMEOUT_MS = 15_000

export const AI_INTERACTION_TIMEOUT_MS = 60_000
export const MESSAGE_SIMULATION_TIMEOUT_MS = AI_INTERACTION_TIMEOUT_MS

function readServerMessage(error) {
  const message = error?.response?.data?.detail || error?.response?.data?.message
  return typeof message === 'string' && message.trim() ? message : ''
}

function isTimeoutError(error) {
  const code = String(error?.code || '').toUpperCase()
  const message = String(error?.message || '')
  return code === 'ECONNABORTED' || /timeout/i.test(message)
}

function isOneMinuteTimeout(error) {
  const timeout = Number(error?.config?.timeout)
  return Number.isFinite(timeout) && timeout >= AI_INTERACTION_TIMEOUT_MS
}

export function normalizeApiErrorMessage(error) {
  const serverMessage = readServerMessage(error)
  if (serverMessage) return serverMessage
  if (isTimeoutError(error)) {
    return isOneMinuteTimeout(error)
      ? '处理超过 1 分钟，已自动超时，请稍后再试'
      : '这次处理有点慢，请稍后再试'
  }
  return error?.message || '请求没成功，请稍后再试'
}

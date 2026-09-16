const DEFAULT_MAX_ATTEMPTS = 3
const DEFAULT_WINDOW_MS = 60 * 1000
let refreshAttemptGuardBypass = false

export function setRefreshAttemptGuardBypass(enabled) {
  refreshAttemptGuardBypass = Boolean(enabled)
}

export function isRefreshAttemptGuardBypassed() {
  return refreshAttemptGuardBypass
}

export function createRefreshAttemptGuard({ maxAttempts = DEFAULT_MAX_ATTEMPTS, windowMs = DEFAULT_WINDOW_MS } = {}) {
  const safeMaxAttempts = Math.max(1, Number(maxAttempts) || DEFAULT_MAX_ATTEMPTS)
  const safeWindowMs = Math.max(1000, Number(windowMs) || DEFAULT_WINDOW_MS)
  let timestamps = []
  let cooldownUntil = 0

  function normalizeNow(now = Date.now()) {
    return Number.isFinite(now) ? now : Date.now()
  }

  function prune(now) {
    timestamps = timestamps.filter((timestamp) => now - timestamp < safeWindowMs)
  }

  function getRemainingMs(now = Date.now()) {
    if (refreshAttemptGuardBypass) return 0

    const currentNow = normalizeNow(now)
    prune(currentNow)

    let remainingMs = cooldownUntil > currentNow ? cooldownUntil - currentNow : 0
    if (timestamps.length >= safeMaxAttempts) {
      remainingMs = Math.max(remainingMs, safeWindowMs - (currentNow - timestamps[0]))
    }

    return Math.max(0, remainingMs)
  }

  return {
    canRun(now = Date.now()) {
      if (refreshAttemptGuardBypass) return true
      return getRemainingMs(now) <= 0
    },
    getRemainingMs,
    getRemainingSeconds(now = Date.now()) {
      const remainingMs = getRemainingMs(now)
      return remainingMs > 0 ? Math.max(1, Math.ceil(remainingMs / 1000)) : 0
    },
    markRun(now = Date.now()) {
      if (refreshAttemptGuardBypass) return 0
      const currentNow = normalizeNow(now)
      prune(currentNow)
      timestamps.push(currentNow)
      return timestamps.length
    },
    setCooldown(seconds, now = Date.now()) {
      if (refreshAttemptGuardBypass) return 0
      const currentNow = normalizeNow(now)
      const safeSeconds = Math.max(0, Math.ceil(Number(seconds) || 0))
      cooldownUntil = Math.max(cooldownUntil, currentNow + safeSeconds * 1000)
      return cooldownUntil
    },
    reset() {
      timestamps = []
      cooldownUntil = 0
    },
  }
}

export function parseRetryAfterSeconds(message) {
  const match = String(message || '').match(/(\d+)\s*秒后再试/)
  return match ? Number(match[1]) : 0
}

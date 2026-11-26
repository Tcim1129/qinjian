const DRAFT_PREFIX = 'qj_draft_v1:'

function resolveStorage(explicitStorage) {
  if (explicitStorage) return explicitStorage
  try {
    return typeof window !== 'undefined' ? window.sessionStorage : null
  } catch {
    return null
  }
}

function tokenFingerprint(token) {
  const raw = String(token || '')
  let hash = 2166136261
  for (let i = 0; i < raw.length; i += 1) {
    hash ^= raw.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

export function buildDraftStorageKey({ surface, ownerId, token, scopeId = 'solo' }) {
  const safeSurface = String(surface || '').trim()
  const safeOwner = String(ownerId || '').trim()
  const safeToken = String(token || '').trim()
  if (!safeSurface || !safeOwner || !safeToken || safeToken === 'demo-mode') {
    return null
  }
  const safeScope = String(scopeId || 'solo').trim() || 'solo'
  return `${DRAFT_PREFIX}${encodeURIComponent(safeSurface)}:${encodeURIComponent(safeOwner)}:${tokenFingerprint(safeToken)}:${encodeURIComponent(safeScope)}`
}

function isEmptyDraftValue(value) {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.length === 0
  if (typeof value === 'object') {
    const draft = typeof value.draft === 'string' ? value.draft : ''
    return !draft && !value.result
  }
  return false
}

export function saveScopedDraft(params, explicitStorage = null) {
  const storage = resolveStorage(explicitStorage)
  const key = buildDraftStorageKey(params)
  if (!storage || !key) return false
  try {
    if (isEmptyDraftValue(params.value)) {
      storage.removeItem(key)
      return true
    }
    const payload = {
      ownerId: String(params.ownerId),
      tokenDigest: tokenFingerprint(params.token),
      scopeId: String(params.scopeId || 'solo') || 'solo',
      value: params.value,
    }
    storage.setItem(key, JSON.stringify(payload))
    return true
  } catch {
    return false
  }
}

export function loadScopedDraft(params, explicitStorage = null) {
  const storage = resolveStorage(explicitStorage)
  const key = buildDraftStorageKey(params)
  if (!storage || !key) return null
  try {
    const raw = storage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (
      !parsed
      || parsed.ownerId !== String(params.ownerId)
      || parsed.tokenDigest !== tokenFingerprint(params.token)
      || parsed.scopeId !== (String(params.scopeId || 'solo') || 'solo')
    ) {
      return null
    }
    return parsed.value ?? null
  } catch {
    return null
  }
}

export function clearScopedDraft(params, explicitStorage = null) {
  const storage = resolveStorage(explicitStorage)
  const key = buildDraftStorageKey(params)
  if (!storage || !key) return
  try {
    storage.removeItem(key)
  } catch {
    // ignore storage errors
  }
}

export function clearAllScopedDrafts(explicitStorage = null) {
  const storage = resolveStorage(explicitStorage)
  if (!storage) return
  try {
    const toRemove = []
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i)
      if (key && key.startsWith(DRAFT_PREFIX)) {
        toRemove.push(key)
      }
    }
    for (const key of toRemove) {
      storage.removeItem(key)
    }
  } catch {
    // ignore storage errors
  }
}

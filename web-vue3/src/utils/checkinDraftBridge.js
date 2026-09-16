import { accountStorageKey, getStorageOwner } from './accountStorage.js'

const CHECKIN_DRAFT_BRIDGE_KEY = 'qj_checkin_prefill_from_chat'

export function saveChatDraftToCheckin(content) {
  const normalizedContent = String(content || '').trim()
  if (!normalizedContent) return false
  const ownerUserId = getStorageOwner()
  const key = accountStorageKey(CHECKIN_DRAFT_BRIDGE_KEY, ownerUserId)
  if (!key) return false
  window.sessionStorage.setItem(
    key,
    JSON.stringify({
      ownerUserId,
      content: normalizedContent,
      savedAt: new Date().toISOString(),
    }),
  )
  return true
}

export function consumeChatDraftToCheckin() {
  const ownerUserId = getStorageOwner()
  const key = accountStorageKey(CHECKIN_DRAFT_BRIDGE_KEY, ownerUserId)
  if (!key) return null
  const raw = window.sessionStorage.getItem(key)
  if (!raw) return null
  try {
    const payload = JSON.parse(raw)
    if (payload.ownerUserId !== ownerUserId) return null
    window.sessionStorage.removeItem(key)
    const content = String(payload?.content || '').trim()
    return content ? { content, savedAt: payload?.savedAt || null } : null
  } catch {
    return null
  }
}

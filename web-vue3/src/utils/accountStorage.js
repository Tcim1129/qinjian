// Identity is bound only after /users/me succeeds, never inferred from a saved draft.
let owner = null

export function setStorageOwner(userId, token) {
  owner = userId && token ? { id: String(userId), token: String(token) } : null
}

export function clearStorageOwner() { owner = null }

export function getStorageOwner() {
  try {
    return owner && window.sessionStorage.getItem('qj_token') === owner.token ? owner.id : ''
  } catch { return '' }
}

export function accountStorageKey(key, ownerId = getStorageOwner()) {
  return ownerId ? `${key}:owner:${encodeURIComponent(ownerId)}` : null
}

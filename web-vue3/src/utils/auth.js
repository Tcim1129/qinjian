import { DEMO_TOKEN } from '../demo/fixtures.js'

const TOKEN_KEY = 'qj_token'
const PERSISTED_TOKEN_KEY = 'qj_persisted_token'
const AUTO_LOGIN_KEY = 'qj_auto_login'
const REMEMBER_PASSWORD_KEY = 'qj_remember_password'
const REMEMBERED_ACCOUNT_KEY = 'qj_remembered_account'
const REMEMBERED_PASSWORD_KEY = 'qj_remembered_password'

function getSessionStorage() {
  if (typeof window === 'undefined') return null
  return window.sessionStorage
}

function getLocalStorage() {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

export function restorePersistedTokenToSession() {
  const local = getLocalStorage()
  const session = getSessionStorage()
  if (!local) return
  clearLegacyRememberedPassword(local)
  clearLegacyPersistedToken(local)
  if (!session || session.getItem(TOKEN_KEY)) return
  if (local.getItem(AUTO_LOGIN_KEY) !== '1') return
}

function clearLegacyRememberedPassword(local) {
  if (local?.getItem(REMEMBERED_PASSWORD_KEY) !== null) {
    local.removeItem(REMEMBERED_PASSWORD_KEY)
  }
}

function clearLegacyPersistedToken(local) {
  if (local?.getItem(PERSISTED_TOKEN_KEY) !== null) {
    local.removeItem(PERSISTED_TOKEN_KEY)
  }
}

export function getAuthToken() {
  restorePersistedTokenToSession()
  return getSessionStorage()?.getItem(TOKEN_KEY) || ''
}

export function isDemoToken(token = getAuthToken()) {
  return token === DEMO_TOKEN
}

export function canUsePasswordCredentialStore() {
  return typeof window !== 'undefined'
    && typeof navigator !== 'undefined'
    && 'PasswordCredential' in window
    && typeof navigator.credentials?.store === 'function'
}

export async function storePasswordCredential({ account = '', password = '' } = {}) {
  const normalizedAccount = String(account || '').trim()
  const normalizedPassword = String(password || '')
  if (!normalizedAccount || !normalizedPassword || !canUsePasswordCredentialStore()) return false

  try {
    const credential = new window.PasswordCredential({
      id: normalizedAccount,
      password: normalizedPassword,
      name: normalizedAccount,
    })
    await navigator.credentials.store(credential)
    return true
  } catch {
    return false
  }
}

export function setAuthToken(
  token,
  { persist = false, clearPersisted = !persist } = {},
) {
  const session = getSessionStorage()
  const local = getLocalStorage()

  if (session) {
    if (token) session.setItem(TOKEN_KEY, token)
    else session.removeItem(TOKEN_KEY)
  }

  if (!local) return

  if (persist && token && token !== DEMO_TOKEN) {
    local.removeItem(PERSISTED_TOKEN_KEY)
    local.setItem(AUTO_LOGIN_KEY, '1')
    return
  }

  if (clearPersisted) {
    local.removeItem(PERSISTED_TOKEN_KEY)
    local.setItem(AUTO_LOGIN_KEY, '0')
  }
}

export function clearAuthToken({ clearPersisted = true } = {}) {
  const session = getSessionStorage()
  const local = getLocalStorage()

  session?.removeItem(TOKEN_KEY)

  if (clearPersisted) {
    local?.removeItem(PERSISTED_TOKEN_KEY)
    local?.setItem(AUTO_LOGIN_KEY, '0')
  }
}

export function loadLoginPreferences() {
  const local = getLocalStorage()
  clearLegacyRememberedPassword(local)
  return {
    autoLogin: local?.getItem(AUTO_LOGIN_KEY) === '1',
    rememberPassword: local?.getItem(REMEMBER_PASSWORD_KEY) === '1',
    account: local?.getItem(REMEMBERED_ACCOUNT_KEY) || '',
    password: '',
  }
}

export function saveLoginPreferences({
  account = '',
  autoLogin = false,
  rememberPassword = false,
}) {
  const local = getLocalStorage()
  if (!local) return

  local.setItem(AUTO_LOGIN_KEY, autoLogin ? '1' : '0')
  local.setItem(REMEMBER_PASSWORD_KEY, rememberPassword ? '1' : '0')

  if (rememberPassword || autoLogin) {
    local.setItem(REMEMBERED_ACCOUNT_KEY, account)
  } else {
    local.removeItem(REMEMBERED_ACCOUNT_KEY)
  }
  local.removeItem(REMEMBERED_PASSWORD_KEY)
}

restorePersistedTokenToSession()

import test from 'node:test'
import assert from 'node:assert/strict'
import {
  canUsePasswordCredentialStore,
  loadLoginPreferences,
  restorePersistedTokenToSession,
  saveLoginPreferences,
  setAuthToken,
  storePasswordCredential,
} from './auth.js'

function createStorage(initial = {}) {
  const store = new Map(Object.entries(initial))
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    snapshot() {
      return Object.fromEntries(store.entries())
    },
  }
}

function installWindow({ local = {}, session = {} } = {}) {
  const windowStub = {
    localStorage: createStorage(local),
    sessionStorage: createStorage(session),
  }
  globalThis.window = windowStub
  return windowStub
}

function cleanupWindow() {
  delete globalThis.window
}

test('saving login preferences never persists the raw password', () => {
  const windowStub = installWindow()
  try {
    saveLoginPreferences({
      account: 'user@example.com',
      password: 'super-secret',
      autoLogin: true,
      rememberPassword: true,
    })

    assert.equal(windowStub.localStorage.getItem('qj_remembered_password'), null)
    assert.equal(windowStub.localStorage.getItem('qj_remembered_account'), 'user@example.com')
    assert.equal(windowStub.localStorage.getItem('qj_remember_password'), '1')
    assert.equal(windowStub.localStorage.getItem('qj_auto_login'), '1')
  } finally {
    cleanupWindow()
  }
})

test('loading login preferences ignores any legacy stored password', () => {
  const windowStub = installWindow({
    local: {
      qj_remember_password: '1',
      qj_remembered_account: 'user@example.com',
      qj_remembered_password: 'legacy-secret',
    },
  })
  try {
    assert.deepEqual(loadLoginPreferences(), {
      autoLogin: false,
      rememberPassword: true,
      account: 'user@example.com',
      password: '',
    })
    assert.equal(windowStub.localStorage.getItem('qj_remembered_password'), null)
  } finally {
    cleanupWindow()
  }
})

test('auto-login keeps the token session-only', () => {
  const windowStub = installWindow()
  try {
    setAuthToken('token-123', { persist: true })

    assert.equal(windowStub.sessionStorage.getItem('qj_token'), 'token-123')
    assert.equal(windowStub.localStorage.getItem('qj_persisted_token'), null)
    assert.equal(windowStub.localStorage.getItem('qj_auto_login'), '1')
    assert.equal(windowStub.localStorage.getItem('qj_remembered_password'), null)
  } finally {
    cleanupWindow()
  }
})

test('legacy persisted tokens are cleared instead of restored', () => {
  const windowStub = installWindow({
    local: {
      qj_auto_login: '1',
      qj_persisted_token: 'legacy-token',
    },
  })
  try {
    restorePersistedTokenToSession()

    assert.equal(windowStub.sessionStorage.getItem('qj_token'), null)
    assert.equal(windowStub.localStorage.getItem('qj_persisted_token'), null)
  } finally {
    cleanupWindow()
  }
})

test('password credential storage is a no-op when the browser API is unavailable', async () => {
  installWindow()
  try {
    assert.equal(canUsePasswordCredentialStore(), false)
    assert.equal(await storePasswordCredential({ account: 'user@example.com', password: 'secret-123' }), false)
  } finally {
    cleanupWindow()
  }
})

test('password credential storage delegates to the browser credential manager when available', async () => {
  installWindow()
  const stored = []
  globalThis.window.PasswordCredential = class PasswordCredential {
    constructor(payload) {
      Object.assign(this, payload)
    }
  }
  const originalNavigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: {
      credentials: {
        async store(credential) {
          stored.push(credential)
        },
      },
    },
  })
  try {
    assert.equal(canUsePasswordCredentialStore(), true)
    assert.equal(await storePasswordCredential({ account: 'user@example.com', password: 'secret-123' }), true)
    assert.deepEqual(stored.map((item) => ({
      id: item.id,
      password: item.password,
      name: item.name,
    })), [{
      id: 'user@example.com',
      password: 'secret-123',
      name: 'user@example.com',
    }])
  } finally {
    if (originalNavigatorDescriptor) {
      Object.defineProperty(globalThis, 'navigator', originalNavigatorDescriptor)
    } else {
      delete globalThis.navigator
    }
    cleanupWindow()
  }
})

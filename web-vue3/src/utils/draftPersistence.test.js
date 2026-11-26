import assert from 'node:assert/strict'
import test from 'node:test'

import {
  clearAllScopedDrafts,
  clearScopedDraft,
  loadScopedDraft,
  saveScopedDraft,
} from './draftPersistence.js'

function createMemoryStorage() {
  const map = new Map()
  return {
    get length() { return map.size },
    key(index) { return Array.from(map.keys())[index] ?? null },
    getItem(key) { return map.has(key) ? map.get(key) : null },
    setItem(key, value) { map.set(key, String(value)) },
    removeItem(key) { map.delete(key) },
  }
}

test('scoped drafts persist across leave/return and stay isolated per partner scope', () => {
  const storage = createMemoryStorage()
  const base = { surface: 'chat', ownerId: 'user-1', token: 'tok-a' }

  saveScopedDraft({ ...base, scopeId: 'pair-a', value: '给小夏写一半的话' }, storage)
  saveScopedDraft({ ...base, scopeId: 'pair-b', value: '给小周写一半的话' }, storage)

  assert.equal(loadScopedDraft({ ...base, scopeId: 'pair-a' }, storage), '给小夏写一半的话')
  assert.equal(loadScopedDraft({ ...base, scopeId: 'pair-b' }, storage), '给小周写一半的话')
  assert.equal(loadScopedDraft({ ...base, scopeId: 'solo' }, storage), null)

  clearScopedDraft({ ...base, scopeId: 'pair-a' }, storage)
  assert.equal(loadScopedDraft({ ...base, scopeId: 'pair-a' }, storage), null)
  assert.equal(loadScopedDraft({ ...base, scopeId: 'pair-b' }, storage), '给小周写一半的话')
})

test('logout wipes all drafts and different account or token cannot read previous drafts', () => {
  const storage = createMemoryStorage()
  saveScopedDraft({ surface: 'message_simulation', ownerId: 'user-1', token: 'tok-1', scopeId: 'solo', value: { draft: '私密草稿' } }, storage)

  assert.equal(loadScopedDraft({ surface: 'message_simulation', ownerId: 'user-2', token: 'tok-2', scopeId: 'solo' }, storage), null)
  assert.equal(loadScopedDraft({ surface: 'message_simulation', ownerId: 'user-1', token: 'tok-relogin', scopeId: 'solo' }, storage), null)

  clearAllScopedDrafts(storage)
  assert.equal(storage.length, 0)
  assert.equal(loadScopedDraft({ surface: 'message_simulation', ownerId: 'user-1', token: 'tok-1', scopeId: 'solo' }, storage), null)
})

test('demo mode tokens never persist drafts to sessionStorage', () => {
  const storage = createMemoryStorage()
  const saved = saveScopedDraft({ surface: 'chat', ownerId: 'demo-user', token: 'demo-mode', scopeId: 'solo', value: '样例草稿' }, storage)
  assert.equal(saved, false)
  assert.equal(storage.length, 0)
})

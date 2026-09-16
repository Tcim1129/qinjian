import test from 'node:test'
import assert from 'node:assert/strict'

import {
  DEFAULT_RELATIONSHIP_SPACE_THEME,
  loadStoredRelationshipSpaceTheme,
  normalizeRelationshipSpaceTheme,
  resolveRelationshipSpaceTheme,
  saveStoredRelationshipSpaceTheme,
} from './relationshipTheme.js'

function createStorage() {
  const data = new Map()

  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null
    },
    setItem(key, value) {
      data.set(key, String(value))
    },
    removeItem(key) {
      data.delete(key)
    },
  }
}

test('normalizeRelationshipSpaceTheme falls back to the classic light theme', () => {
  assert.equal(normalizeRelationshipSpaceTheme('engine'), 'engine')
  assert.equal(normalizeRelationshipSpaceTheme('unknown-theme'), DEFAULT_RELATIONSHIP_SPACE_THEME)
  assert.equal(normalizeRelationshipSpaceTheme(''), DEFAULT_RELATIONSHIP_SPACE_THEME)
})

test('stored relationship space theme is saved and loaded from local storage', () => {
  const storage = createStorage()

  saveStoredRelationshipSpaceTheme('stardust', storage)
  assert.equal(loadStoredRelationshipSpaceTheme(storage), 'stardust')

  saveStoredRelationshipSpaceTheme('broken-value', storage)
  assert.equal(loadStoredRelationshipSpaceTheme(storage), DEFAULT_RELATIONSHIP_SPACE_THEME)
})

test('profile theme wins over local storage while still preserving light fallback', () => {
  const storage = createStorage()
  saveStoredRelationshipSpaceTheme('engine', storage)

  assert.equal(resolveRelationshipSpaceTheme('classic', storage), 'classic')
  assert.equal(resolveRelationshipSpaceTheme('', storage), 'engine')
  assert.equal(resolveRelationshipSpaceTheme(undefined, createStorage()), DEFAULT_RELATIONSHIP_SPACE_THEME)
})

import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveRelationshipDisplayPair } from './relationshipDisplay.js'

test('prefers the active pair when an active and pending pair coexist', () => {
  const activePair = { id: 'pair-active', status: 'active', type: 'couple' }
  const currentPair = { id: 'pair-pending', status: 'pending', type: null }

  const resolved = resolveRelationshipDisplayPair({
    activePair,
    currentPair,
  })

  assert.equal(resolved, activePair)
})

test('falls back to the current pair when there is no active pair', () => {
  const currentPair = { id: 'pair-pending', status: 'pending', type: 'friend' }

  const resolved = resolveRelationshipDisplayPair({
    activePair: null,
    currentPair,
  })

  assert.equal(resolved, currentPair)
})

test('returns null when no relationship is available', () => {
  const resolved = resolveRelationshipDisplayPair()

  assert.equal(resolved, null)
})

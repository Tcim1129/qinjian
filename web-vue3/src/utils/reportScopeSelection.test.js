import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPairQuery, resolveScopedPairId } from './reportScopeSelection.js'

test('resolveScopedPairId prefers the query pair id when it is available', () => {
  const pairId = resolveScopedPairId({
    preferredPairId: 'pair-2',
    fallbackPairId: 'pair-1',
    availablePairs: [{ pair_id: 'pair-1' }, { pair_id: 'pair-2' }],
  })

  assert.equal(pairId, 'pair-2')
})

test('resolveScopedPairId keeps the fallback pair id when preferred id is missing', () => {
  const pairId = resolveScopedPairId({
    preferredPairId: 'pair-9',
    fallbackPairId: 'pair-1',
    availablePairs: [{ pair_id: 'pair-1' }, { pair_id: 'pair-2' }],
  })

  assert.equal(pairId, 'pair-1')
})

test('resolveScopedPairId falls back to the first available pair when needed', () => {
  const pairId = resolveScopedPairId({
    preferredPairId: '',
    fallbackPairId: '',
    availablePairs: ['pair-3', 'pair-4'],
  })

  assert.equal(pairId, 'pair-3')
})

test('buildPairQuery only includes pair_id when there is a valid scoped pair', () => {
  assert.deepEqual(buildPairQuery('pair-7'), { pair_id: 'pair-7' })
  assert.deepEqual(buildPairQuery(''), {})
})

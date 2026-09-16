import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveRelationshipSelection } from './relationshipSelection.js'

test('selecting a normal relationship toggles focus on that relationship', () => {
  assert.deepEqual(
    resolveRelationshipSelection({ nextPairId: 'pair-1', focusPairId: '' }),
    { selectedPairId: 'pair-1', focusPairId: 'pair-1' },
  )

  assert.deepEqual(
    resolveRelationshipSelection({ nextPairId: 'pair-1', focusPairId: 'pair-1' }),
    { selectedPairId: 'pair-1', focusPairId: '' },
  )
})

test('selecting overflow keeps the overflow sidebar reachable', () => {
  assert.deepEqual(
    resolveRelationshipSelection({ nextPairId: '__overflow__', focusPairId: 'pair-1' }),
    { selectedPairId: '__overflow__', focusPairId: '' },
  )
})

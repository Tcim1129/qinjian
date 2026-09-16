import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import test from 'node:test'

const __dirname = dirname(fileURLToPath(import.meta.url))
const userStoreSource = readFileSync(resolve(__dirname, '../stores/user.js'), 'utf8')

function returnedStoreBody(source) {
  const returnMatch = source.match(/return\s*\{([\s\S]*?)\n\s*\}/)
  return returnMatch?.[1] || ''
}

test('user store exposes pair invite actions used by PairPage', () => {
  const returnedBody = returnedStoreBody(userStoreSource)
  assert.match(userStoreSource, /function\s+previewJoinPair\s*\(/)
  assert.match(userStoreSource, /function\s+refreshPairInviteCode\s*\(/)
  assert.match(userStoreSource, /function\s+joinPair\s*\(\s*code\s*,\s*type\s*\)/)
  assert.match(returnedBody, /\bpreviewJoinPair\b/)
  assert.match(returnedBody, /\brefreshPairInviteCode\b/)
})

test('user store exposes current and active pair identifiers used by PairPage', () => {
  const returnedBody = returnedStoreBody(userStoreSource)
  assert.match(userStoreSource, /const\s+activePair\s*=\s*computed\s*\(/)
  assert.match(userStoreSource, /const\s+activePairId\s*=\s*computed\s*\(/)
  assert.match(userStoreSource, /const\s+currentPairId\s*=\s*computed\s*\(/)
  assert.match(returnedBody, /\bactivePairId\b/)
  assert.match(returnedBody, /\bcurrentPairId\b/)
})

test('user store exposes pair change request actions used by RelationshipSpacesPage', () => {
  const returnedBody = returnedStoreBody(userStoreSource)
  const requiredActions = [
    'requestPairTypeChange',
    'createBreakRequest',
    'retainBreakRequest',
    'declineBreakRequest',
    'appendBreakRequestMessage',
    'decideBreakRequestRetention',
    'decidePairChangeRequest',
    'cancelPairChangeRequest',
    'updatePartnerNickname',
  ]

  for (const action of requiredActions) {
    assert.match(userStoreSource, new RegExp(`function\\s+${action}\\s*\\(`))
    assert.match(returnedBody, new RegExp(`\\b${action}\\b`))
  }
})

test('user store wires relaxed test accounts to frontend refresh bypass', () => {
  assert.match(userStoreSource, /setRefreshAttemptGuardBypass/)
  assert.match(userStoreSource, /testing_unrestricted/)
  assert.match(userStoreSource, /const\s+testingUnrestricted\s*=\s*computed\s*\(/)
  assert.match(returnedStoreBody(userStoreSource), /\btestingUnrestricted\b/)
})

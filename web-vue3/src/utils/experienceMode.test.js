import test from 'node:test'
import assert from 'node:assert/strict'

import { featureUnavailableReason, resolveExperienceMode } from './experienceMode.js'

test('resolveExperienceMode treats real users without active pairs as solo experience', () => {
  const mode = resolveExperienceMode()

  assert.equal(mode.dataMode, 'real')
  assert.equal(mode.relationshipScope, 'solo')
  assert.equal(mode.hasPairContext, false)
  assert.equal(mode.canUseOnlineAi, true)
  assert.equal(mode.canUseDualPerspective, false)
})

test('resolveExperienceMode prefers active relationship context when present', () => {
  const mode = resolveExperienceMode({
    activePairId: 'pair-1',
    pairs: [
      { id: 'pair-1', status: 'active' },
      { id: 'pair-2', status: 'active' },
    ],
  })

  assert.equal(mode.relationshipScope, 'pair')
  assert.equal(mode.hasPairContext, true)
  assert.equal(mode.activePairId, 'pair-1')
  assert.equal(mode.canUseMultiRelationship, true)
})

test('resolveExperienceMode marks demo sessions as sample-only even when a pair exists', () => {
  const mode = resolveExperienceMode({
    isDemoMode: true,
    currentPair: { id: 'demo-pair', status: 'active' },
  })

  assert.equal(mode.dataMode, 'demo')
  assert.equal(mode.executionMode, 'sample-only')
  assert.equal(mode.canUseOnlineAi, false)
  assert.equal(mode.canUseVoice, false)
  assert.equal(mode.hasPairContext, true)
})

test('resolveExperienceMode exposes relaxed test account gate bypass', () => {
  const mode = resolveExperienceMode({ testingUnrestricted: true })

  assert.equal(mode.testingUnrestricted, true)
  assert.equal(mode.canBypassFeatureGates, true)
  assert.equal(mode.canUseDualPerspective, false)
})

test('featureUnavailableReason explains pair-only and demo-only boundaries clearly', () => {
  const demoMode = resolveExperienceMode({ isDemoMode: true })
  const soloMode = resolveExperienceMode()

  assert.equal(
    featureUnavailableReason('demo-online', demoMode),
    '样例模式暂不做真实整理。'
  )
  assert.equal(
    featureUnavailableReason('dual-perspective', soloMode),
    '双方都留下记录后才能看双视角。'
  )
  assert.equal(
    featureUnavailableReason('pair-context', soloMode),
    '需要先建立具体关系。'
  )
})

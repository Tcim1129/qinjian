import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveHomeRelationshipView } from './homeMode.js'

test('solo users do not get a relationship graph or placeholder partner label', () => {
  const view = resolveHomeRelationshipView()

  assert.equal(view.kind, 'solo')
  assert.equal(view.sectionLabel, '当前模式')
  assert.equal(view.relationLabel, '单人整理')
  assert.equal(view.showRelationshipTree, false)
})

test('pending relationships stay out of paired graph mode until the other side joins', () => {
  const view = resolveHomeRelationshipView({
    currentPair: {
      type: 'friend',
      status: 'pending',
    },
  })

  assert.equal(view.kind, 'pending')
  assert.equal(view.relationLabel, '朋友 · 等待加入')
  assert.equal(view.showRelationshipTree, false)
  assert.equal(view.partnerMetricLabel, '当前邀请')
})

test('active relationships still render paired context with the real partner name', () => {
  const view = resolveHomeRelationshipView({
    currentPair: {
      type: 'couple',
      status: 'active',
    },
    partnerName: '小林',
  })

  assert.equal(view.kind, 'paired')
  assert.equal(view.relationLabel, '情侣 · 小林')
  assert.equal(view.showRelationshipTree, true)
})

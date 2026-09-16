import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPairStatusSummary } from './pairStatusSummary.js'

test('pending relationship summary stays invite-focused and does not fabricate a score', () => {
  const summary = buildPairStatusSummary({
    pair: {
      id: 'pair-pending',
      type: 'friend',
      status: 'pending',
    },
    isCurrent: true,
    inviteCode: 'A6DL4654LY',
  })

  assert.equal(summary.score, null)
  assert.equal(summary.scoreHeading, '当前状态')
  assert.equal(summary.scoreLabel, '待加入')
  assert.match(summary.trendLabel, /等待加入/)
  assert.match(summary.summary, /等待对方加入/)
  assert.match(summary.nextAction, /邀请码/)
  assert.equal(summary.inviteMode, 'pending')
})

test('active current relationship stays honest when there is no real metric yet', () => {
  const summary = buildPairStatusSummary({
    pair: {
      id: 'pair-active',
      type: 'friend',
      status: 'active',
    },
    isCurrent: true,
    inviteCode: 'A6DL4654LY',
  })

  assert.equal(summary.score, null)
  assert.equal(summary.scoreHeading, '当前状态')
  assert.equal(summary.scoreLabel, '已建立')
  assert.match(summary.trendLabel, /真实记录|已建立/)
  assert.match(summary.summary, /真实记录|已建立/)
  assert.match(summary.nextAction, /记录|专属关系页|时间轴|关系日历/)
  assert.equal(summary.inviteMode, 'active')
})

test('active secondary relationship points the user to open detail instead of inventing analysis', () => {
  const summary = buildPairStatusSummary({
    pair: {
      id: 'pair-secondary',
      type: 'friend',
      status: 'active',
    },
    isCurrent: false,
    inviteCode: '',
  })

  assert.equal(summary.score, null)
  assert.equal(summary.scoreLabel, '已建立')
  assert.match(summary.summary, /已经建立/)
  assert.match(summary.nextAction, /专属关系页|点开/)
  assert.equal(summary.inviteMode, 'none')
})

test('pending break request changes the summary copy to reflect the live workflow', () => {
  const summary = buildPairStatusSummary({
    pair: {
      id: 'pair-break',
      type: 'friend',
      status: 'active',
      pending_change_request: {
        kind: 'break_request',
        phase: 'retaining',
      },
    },
    isCurrent: true,
  })

  assert.equal(summary.scoreHeading, '当前状态')
  assert.equal(summary.scoreLabel, '挽留中')
  assert.equal(summary.trendLabel, '移除流程中')
  assert.match(summary.summary, /挽留阶段/)
  assert.match(summary.nextAction, /专属关系页/)
})

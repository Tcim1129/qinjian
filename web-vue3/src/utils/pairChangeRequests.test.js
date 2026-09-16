import test from 'node:test'
import assert from 'node:assert/strict'

import {
  breakRequestPhaseLabel,
  describePairChangeRequest,
  describePairChangeResult,
  isBreakRequest,
  pairChangeKindLabel,
} from './pairChangeRequests.js'

test('pairChange utilities describe pending break requests clearly', () => {
  const request = {
    kind: 'break_request',
    requester_nickname: '陈一',
    phase: 'awaiting_retention_choice',
  }

  assert.equal(pairChangeKindLabel('break_request'), '移除关系')
  assert.equal(breakRequestPhaseLabel('retaining'), '挽留中')
  assert.equal(isBreakRequest(request), true)
  assert.match(describePairChangeRequest(request), /等待对方决定是否挽留/)
})

test('pairChange utilities describe accepted retention result clearly', () => {
  const request = {
    kind: 'break_request',
    status: 'rejected',
    resolution_reason: 'retention_accepted',
  }

  assert.equal(
    describePairChangeResult(request),
    '最近一次移除关系申请已被接受挽留，关系恢复正常'
  )
})

test('pairChange utilities describe break completion reasons clearly', () => {
  assert.equal(
    describePairChangeResult({
      kind: 'break_request',
      status: 'approved',
      resolution_reason: 'partner_declined',
    }),
    '最近一次移除关系申请已由对方选择不挽留，关系已解除'
  )

  assert.equal(
    describePairChangeResult({
      kind: 'break_request',
      status: 'approved',
      resolution_reason: 'retention_timeout',
    }),
    '最近一次移除关系申请在挽留阶段超时，关系已自动解除'
  )
})

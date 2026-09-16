import test from 'node:test'
import assert from 'node:assert/strict'
import {
  createRefreshAttemptGuard,
  parseRetryAfterSeconds,
  setRefreshAttemptGuardBypass,
} from './refreshGuards.js'

test('refresh guard blocks the fourth attempt inside the same window', () => {
  const guard = createRefreshAttemptGuard({ maxAttempts: 3, windowMs: 60_000 })

  guard.markRun(0)
  guard.markRun(1_000)
  guard.markRun(2_000)

  assert.equal(guard.canRun(3_000), false)
  assert.equal(guard.getRemainingSeconds(3_000), 57)
  assert.equal(guard.canRun(60_001), true)
})

test('refresh guard supports manual cooldowns from backend reminders', () => {
  const guard = createRefreshAttemptGuard()

  guard.setCooldown(12, 1_000)

  assert.equal(guard.canRun(5_000), false)
  assert.equal(guard.getRemainingSeconds(5_000), 8)
  assert.equal(guard.canRun(13_001), true)
})

test('retry-after parser extracts remaining seconds from chinese messages', () => {
  assert.equal(parseRetryAfterSeconds('发送过于频繁，请 45 秒后再试'), 45)
  assert.equal(parseRetryAfterSeconds('邀请码换得太频繁了，请 9 秒后再试'), 9)
  assert.equal(parseRetryAfterSeconds('这次没有等待时间'), 0)
})

test('refresh guard can be globally bypassed for relaxed test accounts', () => {
  const guard = createRefreshAttemptGuard({ maxAttempts: 1, windowMs: 60_000 })

  try {
    setRefreshAttemptGuardBypass(true)

    guard.markRun(0)
    guard.markRun(1_000)
    guard.setCooldown(30, 2_000)

    assert.equal(guard.canRun(3_000), true)
    assert.equal(guard.getRemainingSeconds(3_000), 0)
  } finally {
    setRefreshAttemptGuardBypass(false)
    guard.reset()
  }
})

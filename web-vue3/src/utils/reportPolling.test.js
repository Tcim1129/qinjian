import test from 'node:test'
import assert from 'node:assert/strict'
import { createReportPoller } from './reportPolling.js'

test('polls pending reports until complete, then stops', async () => {
  const queued = []
  const results = []
  let reads = 0
  const poller = createReportPoller({ schedule: fn => { queued.push(fn); return fn }, cancel() {} })
  poller.start({ read: async () => ({ status: ++reads < 3 ? 'pending' : 'completed' }), onResult: r => results.push(r.status) })
  while (queued.length) await queued.shift()()
  assert.equal(reads, 3)
  assert.deepEqual(results, ['pending', 'pending', 'completed'])
})
test('scope changes discard queued timers and late responses', async () => {
  const queued = []
  let resolve
  let delivered = 0
  const poller = createReportPoller({ schedule: fn => { queued.push(fn); return fn }, cancel() {} })
  poller.start({ read: () => new Promise(r => { resolve = r }), onResult: () => delivered++ })
  const pending = queued.shift()()
  poller.stop()
  resolve({ status: 'completed' })
  await pending
  assert.equal(delivered, 0)
  assert.equal(queued.length, 0)
})
test('stops on failure or bounded timeout without endless requests', async () => {
  for (const status of ['failed', 'pending']) {
    const queued = []
    let ticks = 0, expired = 0
    const poller = createReportPoller({ schedule: fn => { queued.push(fn); return fn }, cancel() {}, now: () => ticks++ * 1000, maxWaitMs: 2000 })
    poller.start({ read: async () => ({ status }), onResult() {}, onTimeout: () => expired++ })
    while (queued.length) await queued.shift()()
    assert.equal(expired, status === 'pending' ? 1 : 0)
  }
})

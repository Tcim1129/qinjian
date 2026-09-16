import test from 'node:test'
import assert from 'node:assert/strict'
import { buildDemoSchedule, buildScheduleContext, scheduleDate, createLatestRequest, createDemoScheduleCache } from './taskSchedule.js'

test('明日安排独立生成，不继承今日完成状态或手动安排', () => {
  const base = { tasks: [{ id: 'a', title: '今日记录', source: 'system', status: 'completed', feedback: { note: '很好' } }, { id: 'b', source: 'manual', title: '今天的约定' }] }
  const today = buildDemoSchedule(base, 'today', new Date(2026, 11, 31, 12))
  const tomorrow = buildDemoSchedule(base, 'tomorrow', new Date(2026, 11, 31, 12))
  assert.equal(today.for_date, '2026-12-31')
  assert.equal(tomorrow.for_date, '2027-01-01')
  assert.notEqual(today.tasks[0].title, tomorrow.tasks[0].title)
  assert.ok(tomorrow.tasks.every(t => t.due_date === tomorrow.for_date && t.status === 'pending' && !t.feedback))
  assert.ok(tomorrow.tasks.every(t => t.source === 'system' && !today.tasks.some(x => x.id === t.id)))
  assert.equal(base.tasks[0].status, 'completed')
  assert.equal(base.tasks[0].due_date, undefined)
})
test('日期按本地日历跨月推进', () => {
  assert.equal(scheduleDate('tomorrow', new Date(2028, 1, 28, 23)), '2028-02-29')
})
test('智能体只带入所选日期和可见安排，空列表不冒充今日安排', () => {
  const ctx = buildScheduleContext([], { scope: 'tomorrow', date: '2026-09-07', pairId: 'p1', isDemoMode: true })
  assert.equal(ctx.pairId, 'p1')
  assert.match(ctx.sourceLabel, /2026-09-07/)
  assert.match(ctx.sourceLabel, /样例/)
  assert.match(ctx.summary, /暂无安排/)
  const task = buildScheduleContext([{ title: '散步', description: '十分钟', status: 'completed', secret: '隐藏字段' }], { date: '2026-09-06', pairId: 'p2' })
  assert.match(task.summary, /散步/)
  assert.match(task.summary, /已完成/)
  assert.doesNotMatch(task.summary, /隐藏字段/)
})
test('切换日期或卸载后，旧请求不能回填新列表', () => {
  const requests = createLatestRequest()
  const old = requests.begin()
  const current = requests.begin()
  assert.equal(old(), false)
  assert.equal(current(), true)
  requests.invalidate()
  assert.equal(current(), false)
})

test('样例安排按成员、关系和日期隔离，切换日期不丢完成状态', () => {
  const cache = createDemoScheduleCache()
  const scope = { owner: 'u1', pairId: 'p1', date: '2026-09-06' }
  const payload = { tasks: [{ id: 'a', status: 'completed' }] }
  cache.save(scope, payload)
  payload.tasks[0].status = 'pending'
  assert.equal(cache.read(scope).tasks[0].status, 'completed')
  assert.equal(cache.read({ ...scope, date: '2026-09-07' }), null)
  assert.equal(cache.read({ ...scope, pairId: 'p2' }), null)
  assert.equal(cache.read({ ...scope, owner: 'u2' }), null)
  assert.equal(cache.read(scope), null)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { createSavedExpressions } from './savedExpressions.js'

const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
function workspace(api) {
  let id = 0
  const store = createSavedExpressions(api, { makeId: () => `request-${++id}` })
  store.setScope({ key: 'alice', pairId: 'pair-a', enabled: true })
  return store
}

test('failed save keeps a stable retry identity and uses final edited text', async () => {
  const calls = []
  const store = workspace({ saveExpression: async (id, data) => {
    calls.push({ id, data })
    if (calls.length === 1) throw new Error('未保存')
    return { id, ...data, created_at: '2026-09-21T00:00:00Z' }
  } })
  assert.equal(await store.save('  我修改后的话\n保留换行。  '), false)
  assert.equal(store.state.items.length, 0)
  assert.equal(store.state.saveError, '未保存')
  await store.save('  我修改后的话\n保留换行。  ')
  assert.deepEqual(calls[1], calls[0])
  assert.equal(calls[1].data.text, '我修改后的话\n保留换行。')
  assert.equal(store.state.items.length, 1)
  await store.save('我修改后的话\n保留换行。')
  assert.equal(calls.length, 2)
  await store.save('另一版')
  assert.notEqual(calls[2].id, calls[0].id)
})

test('double clicks cannot start two saves', async () => {
  const wait = deferred()
  let calls = 0
  const store = workspace({ saveExpression: async (id, payload) => { calls++; await wait.promise; return { id, ...payload } } })
  const saving = store.save('原话')
  assert.equal(await store.save('原话'), false)
  assert.equal(calls, 1)
  wait.resolve()
  await saving
  assert.equal(store.state.saving, false)
})

test('blank, oversized, and sample saves never call the backend', async () => {
  const store = workspace({ saveExpression: () => assert.fail('unexpected write') })
  assert.equal(await store.save('   '), false)
  assert.equal(await store.save('字'.repeat(2001)), false)
  store.setScope({ key: 'sample', pairId: null, enabled: false })
  assert.equal(await store.save('样例'), false)
  await store.load()
  assert.deepEqual([...store.state.items], [])
})

test('A to B to A still discards the first account response', async () => {
  const wait = deferred()
  const store = workspace({ listExpressions: () => wait.promise })
  const loading = store.load()
  store.setScope({ key: 'bob', pairId: 'pair-b', enabled: true })
  store.setScope({ key: 'alice', pairId: 'pair-a', enabled: true })
  wait.resolve([{ id: 'old', text: '上一轮的结果' }])
  await loading
  assert.deepEqual([...store.state.items], [])
  assert.equal(store.state.loading, false)
})

test('old list response cannot erase a newly saved expression', async () => {
  const wait = deferred()
  const store = workspace({ listExpressions: () => wait.promise, saveExpression: async (id, data) => ({ id, ...data }) })
  const loading = store.load()
  await store.save('已保存')
  wait.resolve([])
  await loading
  assert.equal(store.state.items[0].text, '已保存')
  assert.equal(store.state.loading, false)
})

test('account switching discards a pending save and its error state', async () => {
  const wait = deferred()
  const store = workspace({ saveExpression: () => wait.promise })
  const saving = store.save('Alice 的话')
  store.setScope({ key: 'bob', pairId: null, enabled: true })
  wait.reject(new Error('旧请求失败'))
  await saving
  assert.equal(store.state.saveError, '')
  assert.equal(store.state.savedText, '')
  assert.deepEqual([...store.state.items], [])
})

test('delete failure preserves the entry; success invalidates pending lists and retry id', async () => {
  let fail = true
  const store = workspace({
    saveExpression: async (id, data) => ({ id, ...data }),
    deleteExpression: async () => { if (fail) throw new Error('删除失败') },
  })
  await store.save('这句话')
  assert.equal(await store.remove('request-1'), false)
  assert.equal(store.state.items.length, 1)
  fail = false
  await store.remove('request-1')
  assert.deepEqual([...store.state.items], [])
  assert.equal(store.state.savedText, '')
  await store.save('这句话')
  assert.equal(store.state.items[0].id, 'request-2')
})

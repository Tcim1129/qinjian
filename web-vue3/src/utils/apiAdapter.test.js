import test from 'node:test'
import assert from 'node:assert/strict'
import axios from 'axios'

let errorHandler
let defaults
const requests = []
axios.create = config => {
  defaults = config
  const client = { interceptors: { request: { use() {} }, response: { use(_, reject) { errorHandler = reject } } } }
  for (const method of ['get', 'post', 'patch', 'delete']) client[method] = (...args) => {
    requests.push({ method, args }); return Promise.resolve({})
  }
  return client
}
global.sessionStorage = { getItem: () => 'real-token' }
const { api } = await import('../api/index.js')

test('tree collection uses the real endpoint and explicit node key', async () => {
  await api.collectTreeEnergy('pair-a', 'checkin')
  const request = requests.at(-1)
  assert.equal(request.method, 'post')
  assert.equal(request.args[0], '/tree/collect')
  assert.deepEqual(request.args[1], { node_key: 'checkin' })
  assert.equal(request.args[2].params.pair_id, 'pair-a')
})
test('model-backed calls wait longer than normal API requests', async () => {
  for (const run of [() => api.chatWithAgent('session', '你好'), () => api.getDailyTasks('pair'), () => api.refreshTask('task')]) {
    await run()
    assert.ok(requests.at(-1).args.at(-1).timeout >= 60000)
  }
  assert.equal(defaults.timeout, 15000)
})
test('errors preserve rate-limit metadata and have readable timeout messages', async () => {
  await assert.rejects(errorHandler({ response: { status: 429, data: { detail: '请稍后再试' }, headers: { 'retry-after': '12' } } }), error => {
    assert.equal(error.statusCode, 429)
    assert.equal(error.retryAfter, 12)
    return true
  })
  await assert.rejects(errorHandler({ code: 'ECONNABORTED', message: 'timeout of 15000ms exceeded' }), error => {
    assert.equal(error.code, 'ECONNABORTED')
    assert.equal(error.message.includes('15000ms'), false)
    return true
  })
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { registerHooks } from 'node:module'
import { createPinia, setActivePinia } from 'pinia'

registerHooks({ resolve(specifier, context, next) {
  if (specifier.startsWith('@/')) specifier = new URL(`../${specifier.slice(2)}${specifier === '@/api' ? '/index' : ''}.js`, import.meta.url).href
  return next(specifier, context)
} })
const { api } = await import('../api/index.js')
const { useReportStore } = await import('../stores/report.js')
const { useHomeStore } = await import('../stores/home.js')
const { useUserStore } = await import('../stores/user.js')
const { useCheckinStore } = await import('../stores/checkin.js')
const storage = () => { const m = new Map(); return { getItem: k => m.get(k) ?? null, setItem: (k,v) => m.set(k,v), removeItem: k => m.delete(k) } }
const setup = () => { global.window = { sessionStorage: storage(), localStorage: storage() }; global.sessionStorage = window.sessionStorage; global.localStorage = window.localStorage; window.sessionStorage.setItem('qj_token', 'alice'); setActivePinia(createPinia()) }
test('a late report response cannot overwrite a newer relationship or resurrect after logout', async () => {
  setup()
  const pending = []
  api.getLatestReport = () => new Promise(resolve => pending.push(resolve))
  const store = useReportStore()
  const a = store.loadLatest('a'), b = store.loadLatest('b')
  pending[1]({ id: 'b' }); await b
  pending[0]({ id: 'a' }); await a
  assert.equal(store.currentReport.id, 'b')
  const late = store.loadLatest('b')
  store.reset()
  pending[2]({ id: 'private' }); await late
  assert.equal(store.currentReport, null)
})
test('tree collection adds exactly the server points, not invented decay recovery', async () => {
  setup()
  api.getTodayStatus = api.getCheckinStreak = api.getCrisisStatus = async () => ({})
  api.getDailyTasks = async () => ({ tasks: [] })
  api.getMilestones = async () => []
  api.getTreeStatus = async () => ({ growth_points: 100, next_level_at: 200, last_watered: '2020-01-01' })
  const store = useHomeStore()
  await store.loadAll('pair')
  assert.equal(store.tree.effective_growth_points, 100)
  assert.equal(store.tree.decay_points, 0)
  api.collectTreeEnergy = async () => ({ growth_points: 110, points_added: 10, last_watered: '2026-09-06' })
  await store.collectTreeEnergy('pair', 'my_record')
  assert.equal(store.tree.effective_growth_points, 110)
})

test('a profile save finishing after account switch cannot replace the new user', async () => {
  setup()
  let resolve
  api.updateMe = () => new Promise(done => { resolve = done })
  const store = useUserStore()
  store.me = { id: 'alice', nickname: '甲' }
  const save = store.updateMe({ nickname: '甲的新名字' })
  store.logout()
  store.token = 'bob'; sessionStorage.setItem('qj_token', 'bob')
  store.me = { id: 'bob', nickname: '乙' }
  resolve({ id: 'alice', nickname: '甲的新名字' })
  await save
  assert.equal(store.me.id, 'bob')
})

test('a delayed pair mutation cannot add the previous account relationship to the new account', async () => {
  setup()
  let resolve
  api.createPair = () => new Promise(done => { resolve = done })
  const store = useUserStore()
  const creating = store.createPair('couple')
  store.logout()
  store.token = 'bob'; sessionStorage.setItem('qj_token', 'bob')
  resolve({ id: 'alice-pair', status: 'pending' })
  await creating
  assert.deepEqual(store.pairs, [])
  assert.equal(store.currentPair, null)
})

test('logout clears cached personal reports and late checkin history stays cleared', async () => {
  setup()
  const user = useUserStore(), reports = useReportStore(), checkin = useCheckinStore()
  reports.currentReport = { id: 'private-report' }
  let resolve
  api.getCheckinHistory = () => new Promise(done => { resolve = done })
  const reading = checkin.loadHistory('pair-a')
  user.logout()
  assert.equal(reports.currentReport, null)
  resolve([{ content: '上个账号的记录' }]); await reading
  assert.deepEqual(checkin.history, [])
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { setStorageOwner, clearStorageOwner } from './accountStorage.js'
import { saveChatDraftToCheckin, consumeChatDraftToCheckin } from './checkinDraftBridge.js'
import { createSoloTaskEntry, loadSoloTaskPack, createSoloMilestoneEntry, loadSoloMilestoneEntries, createSoloConnectionActivityEntry, loadSoloConnectionWorkspace, saveSoloTaskResultEntry } from './soloWorkspace.js'

const storage = () => { const map = new Map(); return { getItem: k => map.get(k) ?? null, setItem: (k,v) => map.set(k,String(v)), removeItem: k => map.delete(k) } }
test('drafts and all solo records stay with the authenticated account', () => {
  global.window = { localStorage: storage(), sessionStorage: storage() }
  const login = id => { window.sessionStorage.setItem('qj_token', id); setStorageOwner(id, id) }
  login('alice')
  saveChatDraftToCheckin('只给自己的草稿')
  createSoloTaskEntry({ title: '私人的安排' })
  createSoloMilestoneEntry({ title: '纪念日', date: '2026-09-06' })
  createSoloConnectionActivityEntry('chat', '私人计划')
  login('bob')
  assert.equal(consumeChatDraftToCheckin(), null)
  assert.equal(loadSoloTaskPack().tasks.some(t => t.title === '私人的安排'), false)
  assert.deepEqual(loadSoloMilestoneEntries(), [])
  assert.deepEqual(loadSoloConnectionWorkspace().activities, [])
  login('alice')
  assert.equal(consumeChatDraftToCheckin().content, '只给自己的草稿')
  assert.equal(loadSoloTaskPack().tasks.some(t => t.title === '私人的安排'), true)
  assert.equal(loadSoloMilestoneEntries()[0].title, '纪念日')
  assert.equal(loadSoloConnectionWorkspace().activities[0].title, '私人计划')
  clearStorageOwner()
  assert.equal(saveChatDraftToCheckin('未登录'), false)
})

test('unowned legacy data is neither adopted nor deleted; token changes invalidate identity', () => {
  global.window = { localStorage: storage(), sessionStorage: storage() }
  window.sessionStorage.setItem('qj_token', 'a')
  setStorageOwner('alice', 'a')
  window.sessionStorage.setItem('qj_checkin_prefill_from_chat', JSON.stringify({ content: '旧草稿' }))
  window.localStorage.setItem('qj_solo_milestones_v1', JSON.stringify([{ title: '旧记录' }]))
  assert.equal(consumeChatDraftToCheckin(), null)
  assert.deepEqual(loadSoloMilestoneEntries(), [])
  assert.ok(window.localStorage.getItem('qj_solo_milestones_v1'))
  assert.ok(window.sessionStorage.getItem('qj_checkin_prefill_from_chat'))
  window.sessionStorage.setItem('qj_token', 'b')
  assert.equal(saveChatDraftToCheckin('不能仍属于 alice'), false)
  clearStorageOwner()
})

test('solo result survives reopening, preserves uncertainty, and never writes another account', () => {
  global.window = { localStorage: storage(), sessionStorage: storage() }
  window.sessionStorage.setItem('qj_token', 'alice')
  setStorageOwner('alice', 'alice')
  const task = createSoloTaskEntry({ title: '聊聊近况' }).tasks.find(item => item.title === '聊聊近况')
  saveSoloTaskResultEntry(task.id, { status: 'completed', feedback: null })
  assert.equal(loadSoloTaskPack().tasks.find(item => item.id === task.id).needs_feedback, true)
  saveSoloTaskResultEntry(task.id, { status: 'completed', feedback: { outcome: 'uncertain', note: '还不知道有没有帮助' } })
  assert.equal(loadSoloTaskPack().tasks.find(item => item.id === task.id).feedback.outcome, 'uncertain')
  saveSoloTaskResultEntry(task.id, { status: 'pending', feedback: { outcome: 'not_yet', note: '记错了' } })
  assert.equal(loadSoloTaskPack().tasks.find(item => item.id === task.id).completed_at, null)
  window.sessionStorage.setItem('qj_token', 'bob')
  setStorageOwner('bob', 'bob')
  assert.throws(() => saveSoloTaskResultEntry(task.id, { status: 'completed', feedback: null }))
  clearStorageOwner()
})

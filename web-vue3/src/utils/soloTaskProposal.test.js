import test from 'node:test'
import assert from 'node:assert/strict'
import { setStorageOwner, clearStorageOwner } from './accountStorage.js'
import { confirmSoloTaskProposal, findSoloTaskProposal, loadSoloTaskPack } from './soloWorkspace.js'
import { scheduleDate } from './taskSchedule.js'

test('explicit solo confirmation saves once, survives reread and stays with its owner', () => {
  const data = new Map()
  let token = 'qa-token-a'
  globalThis.window = { localStorage: { getItem: k => data.get(k) || null, setItem: (k,v) => data.set(k,String(v)) }, sessionStorage: { getItem: () => token } }
  const proposal = { proposal_id: '00000000-0000-4000-8000-000000000001', title: '今晚散步十分钟', description: '只在自己愿意时进行。', due_date: scheduleDate('today') }
  try {
    setStorageOwner('qa-a', token)
    assert.equal(findSoloTaskProposal(proposal.proposal_id), null)
    const saved = confirmSoloTaskProposal(proposal)
    assert.equal(confirmSoloTaskProposal(proposal).id, saved.id)
    assert.equal(loadSoloTaskPack().tasks.filter(t => t.agent_proposal_id === proposal.proposal_id).length, 1)
    assert.equal(findSoloTaskProposal(proposal.proposal_id).title, proposal.title)
    token = 'qa-token-b'
    setStorageOwner('qa-b', token)
    assert.equal(findSoloTaskProposal(proposal.proposal_id), null)
    assert.ok(!loadSoloTaskPack().tasks.some(t => t.id === saved.id))
  } finally { clearStorageOwner(); delete globalThis.window }
})

test('solo confirmation reports storage failure instead of pretending a task was saved', () => {
  globalThis.window = { sessionStorage: { getItem: () => 'qa-token' }, localStorage: { getItem: () => null, setItem: () => { throw new Error('full') } } }
  try {
    setStorageOwner('qa-storage', 'qa-token')
    assert.throws(() => confirmSoloTaskProposal({ proposal_id: '00000000-0000-4000-8000-000000000002', title: '一件小事', due_date: scheduleDate('today') }), /保存/)
  } finally { clearStorageOwner(); delete globalThis.window }
})

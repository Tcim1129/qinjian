import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'

const utilityUrl = new URL('./contextAgent.js', import.meta.url)

test('context prompts contain the selected source and question without forwarding hidden payloads', async () => {
  assert.ok(existsSync(utilityUrl), 'selected-context prompt helper is missing')
  const { buildContextPrompt } = await import(utilityUrl)
  const result = buildContextPrompt({ sourceLabel: '3月19日的记录', summary: '我们说开了一次误会。', question: '下次怎么开口？', payload: { secret: 'PRIVATE' } })
  assert.match(result, /3月19日的记录/)
  assert.match(result, /下次怎么开口/)
  assert.match(result, /不代表对方真实想法/)
  assert.doesNotMatch(result, /PRIVATE/)
  assert.ok(buildContextPrompt({ summary: '字'.repeat(9000) }).length < 4500)
})

test('context cannot be carried to a different relationship', async () => {
  assert.ok(existsSync(utilityUrl), 'context scope guard is missing')
  const { isContextScopeCurrent } = await import(utilityUrl)
  assert.equal(isContextScopeCurrent({ pairId: 'a' }, 'a'), true)
  assert.equal(isContextScopeCurrent({ pairId: 'a' }, 'b'), false)
  assert.equal(isContextScopeCurrent({ pairId: null }, null), true)
  assert.equal(isContextScopeCurrent({ pairId: null }, 'b'), false)
})

test('record contexts only use accessible active relationships', async () => {
  const { isContextScopeAvailable } = await import(utilityUrl)
  const pairs = [{ id: 'a', status: 'active' }, { id: 'b', status: 'ended' }]
  assert.equal(isContextScopeAvailable({ pairId: 'a' }, 'a', pairs), true)
  assert.equal(isContextScopeAvailable({ pairId: 'a' }, 'c', pairs), true)
  assert.equal(isContextScopeAvailable({ pairId: 'b' }, 'b', pairs), false)
  assert.equal(isContextScopeAvailable({ pairId: 'unknown' }, 'unknown', pairs), false)
  assert.equal(isContextScopeAvailable({ pairId: null }, null, []), true)
  assert.equal(isContextScopeAvailable({ pairId: null }, 'a', pairs), false)
})

test('alignment prompts preserve speaker labels and date without inventing first-person ownership', async () => {
  const { buildAlignmentContext } = await import(utilityUrl)
  const record = { checkin_date: '2026-03-21', user_a_label: '甲', user_b_label: '乙', view_a_summary: '需要休息', view_b_summary: '想聊聊', suggested_opening: '今晚方便吗', bridge_actions: ['先问时间'], hidden_record: 'PRIVATE' }
  const compare = buildAlignmentContext(record, 'compare', { pairId: 'a', isDemoMode: true })
  assert.equal(compare.pairId, 'a')
  assert.match(compare.sourceLabel, /2026-03-21/)
  assert.match(compare.sourceLabel, /样例/)
  assert.match(compare.summary, /甲：需要休息/)
  assert.match(compare.summary, /乙：想聊聊/)
  assert.doesNotMatch(compare.summary, /PRIVATE/)
  const opening = buildAlignmentContext(record, 'opening', { pairId: 'a' })
  assert.match(opening.summary, /今晚方便吗/)
  const action = buildAlignmentContext(record, 'action', { pairId: 'a' })
  assert.match(action.summary, /先问时间/)
  assert.notEqual(action.question, opening.question)
})

test('late session results are rejected after account, relationship, or component lifetime changes', async () => {
  const { isChatScopeCurrent } = await import(utilityUrl)
  const source = { token: 'session-a', userId: 'user-a', pairId: 'pair-a' }
  assert.equal(isChatScopeCurrent(source, { ...source }), true)
  assert.equal(isChatScopeCurrent(source, { ...source, token: 'session-b' }), false)
  assert.equal(isChatScopeCurrent(source, { ...source, userId: 'user-b' }), false)
  assert.equal(isChatScopeCurrent(source, { ...source, pairId: 'pair-b' }), false)
  assert.equal(isChatScopeCurrent(source, { ...source, disposed: true }), false)
  assert.equal(isChatScopeCurrent({ ...source, revision: 1 }, { ...source, revision: 3 }), false)
})
test('alignment context supports customized perspective labels and summaries', async () => {
  const { buildAlignmentContext } = await import(utilityUrl)
  const record = { checkin_date: '2026-03-21', user_a_label: '陈一', user_b_label: '顾遥', view_a_summary: '陈一观点', view_b_summary: '顾遥观点' }
  const custom = buildAlignmentContext(record, 'compare', {
    pairId: '99999999-9999-4999-8999-999999999999',
    myLabel: '顾遥',
    partnerLabel: '陈一',
    mySummary: '顾遥的自述',
    partnerSummary: '陈一的自述',
  })
  assert.match(custom.summary, /我（顾遥）：顾遥的自述/)
  assert.match(custom.summary, /对方（陈一）：陈一的自述/)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { requestSceneReply } from './requestSceneReply.js'

test('rewriting forwards actual source and returns only received output', async () => {
  let payload
  const api = { createAgentSession: async id => { assert.equal(id, 'pair'); return { session_id: 's' } }, chatWithAgent: async (id, data) => { payload = data; return { reply: '明天再聊好吗？' } } }
  assert.equal(await requestSceneReply(api, 'pair', { summary: '我今晚想休息' }, '换一种说法'), '明天再聊好吗？')
  assert.equal(payload.scene_context.summary, '我今晚想休息')
  assert.equal(payload.scene_context.intent, 'wording')
})
test('provider errors, empty replies and stale scopes do not produce preset replies', async () => {
  const api = { createAgentSession: async () => ({ id: 's' }), chatWithAgent: async () => { throw new Error('offline') } }
  await assert.rejects(requestSceneReply(api, 'p', {}, '改写'), /offline/)
  api.chatWithAgent = async () => ({ reply: '' })
  await assert.rejects(requestSceneReply(api, 'p', {}, '改写'), /没有收到/)
  let current = true
  api.createAgentSession = async () => { current = false; return { id: 's' } }
  api.chatWithAgent = async () => { assert.fail('must not call model after scope changed') }
  await assert.rejects(requestSceneReply(api, 'p', {}, '改写', () => current), /页面已切换/)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeChatHistory } from './chatHistory.js'

test('history deduplicates by turn identity, not by matching words', () => {
  const pending = { id: 'local-user-b', clientMessageId: 'b', content: '再说说', deliveryPending: true }
  const first = { id: 'a', role: 'user', content: '再说说' }
  const result = mergeChatHistory([first, { id: 'b', payload: { _delivery: { state: 'processing' } } }], [pending])
  assert.equal(result.length, 2)
  assert.equal(result[1], pending)
  assert.deepEqual(mergeChatHistory([first], [pending]), [first, pending])
})

test('confirmed history wins over an ambiguous local error', () => {
  const saved = { id: 'a', payload: { _delivery: { state: 'completed' } } }
  assert.deepEqual(mergeChatHistory([saved], [{ id: 'local-user-a', clientMessageId: 'a', error: true }]), [saved])
})

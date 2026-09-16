import test from 'node:test'
import assert from 'node:assert/strict'
import { getDemoNarrativeAlignment } from '../demo/fixtures.js'

test('getDemoNarrativeAlignment returns specific narrative alignment for partner, friend, and companion', () => {
  // 1. 林夏 (partner)
  const linxia = getDemoNarrativeAlignment('22222222-2222-4222-8222-222222222222')
  assert.ok(linxia)
  assert.equal(linxia.user_b_label, '林夏')
  assert.match(linxia.shared_story, /太累了|重要吗/)

  // 2. 周宁 (friend)
  const zhouning = getDemoNarrativeAlignment('77777777-7777-4777-8777-777777777777')
  assert.ok(zhouning)
  assert.equal(zhouning.user_b_label, '周宁')
  assert.match(zhouning.shared_story, /老友|爽约/)

  // 3. 顾遥 (companion)
  const guyao = getDemoNarrativeAlignment('99999999-9999-4999-8999-999999999999')
  assert.ok(guyao)
  assert.equal(guyao.user_b_label, '顾遥')
  assert.match(guyao.shared_story, /搭子|节奏/)

  // 4. fallback when null
  const fallback = getDemoNarrativeAlignment(null)
  assert.ok(fallback)
  assert.equal(fallback.user_b_label, '林夏')
})

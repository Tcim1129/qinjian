import test from 'node:test'
import assert from 'node:assert/strict'

import { buildRelationshipSpaces } from './relationshipSpaces.js'

test('relationship spaces stay empty for users without any relationships', () => {
  assert.deepEqual(buildRelationshipSpaces(), [])
})

test('active relationship spaces use the real pair data instead of demo fixtures', () => {
  const spaces = buildRelationshipSpaces({
    me: { nickname: '阿青' },
    pairs: [
      {
        id: 'pair-1',
        type: 'bestfriend',
        status: 'active',
        custom_partner_nickname: '周宁',
      },
    ],
  })

  assert.equal(spaces.length, 1)
  assert.equal(spaces[0].type, '挚友')
  assert.equal(spaces[0].title, '周宁')
  assert.deepEqual(spaces[0].people, ['阿青', '周宁'])
  assert.equal(spaces[0].signal, '已建立')
})

test('pending relationship spaces explain that the other side has not joined yet', () => {
  const spaces = buildRelationshipSpaces({
    me: { nickname: '阿青' },
    pairs: [
      {
        id: 'pair-2',
        type: 'friend',
        status: 'pending',
      },
    ],
  })

  assert.equal(spaces.length, 1)
  assert.equal(spaces[0].type, '朋友')
  assert.deepEqual(spaces[0].people, ['阿青', '等待加入'])
  assert.equal(spaces[0].signal, '待加入')
  assert.match(spaces[0].prompt, /邀请码/)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import {
  RELATIONSHIP_PROFILE_ACTIONS,
  RELATIONSHIP_SEARCH_ITEMS,
  buildSearchResults,
  getRelationshipSearchItems,
} from './relationshipShortcuts.js'
import {
  RELATIONSHIP_INVITE_ROUTE,
  RELATIONSHIP_JOIN_ROUTE,
  RELATIONSHIP_LIST_ROUTE,
  RELATIONSHIP_MANAGEMENT_ROUTE,
  LEGACY_RELATIONSHIP_PATHS,
} from './relationshipRouting.js'

test('profile relationship shortcuts expose separate view, invite, and join destinations', () => {
  assert.deepEqual(RELATIONSHIP_PROFILE_ACTIONS, [
    {
      label: '查看关系',
      desc: '查看或切换当前关系',
      to: RELATIONSHIP_LIST_ROUTE,
      sectionId: 'pair-list',
    },
    {
      label: '发起邀请',
      desc: '创建邀请码发给对方',
      to: RELATIONSHIP_INVITE_ROUTE,
      sectionId: 'pair-create',
    },
    {
      label: '输入邀请码',
      desc: '输入邀请码加入关系',
      to: RELATIONSHIP_JOIN_ROUTE,
      sectionId: 'pair-join',
    },
  ])
})

test('relationship search items include dedicated view, invite, join, and management entries', () => {
  const items = getRelationshipSearchItems()
  assert.equal(items.length, 4)
  assert.ok(items.every((item) => item.to.startsWith('/pair')))
  assert.equal(items[0].label, '关系')
  assert.equal(items[1].label, '关系')
  assert.equal(items[2].label, '关系')
  assert.equal(items[3].label, '关系')
  assert.equal(items[0].title, '查看当前关系')
  assert.equal(items[1].title, '发邀请码给对方')
  assert.equal(items[2].title, '输入收到的邀请码')
  assert.equal(items[3].title, '打开关系总入口')
  assert.equal(items[0].to, RELATIONSHIP_LIST_ROUTE)
  assert.ok(items.some((item) => item.keywords.includes('查看关系')))
  assert.ok(items.some((item) => item.keywords.includes('发起邀请')))
  assert.ok(items.some((item) => item.keywords.includes('输入邀请码')))
  assert.ok(items[1].keywords.includes('邀请代码'))
  assert.ok(items[2].keywords.includes('加入关系'))
  assert.equal(items[3].to, RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.deepEqual(items, RELATIONSHIP_SEARCH_ITEMS)
})

test('buildSearchResults merges duplicate search entries for the same route and keeps distinct relation entry points', () => {
  const items = [
    ...RELATIONSHIP_SEARCH_ITEMS,
    {
      label: '我的',
      title: '我的关系入口',
      desc: '旧入口，仍然会跳到关系总入口。',
      to: LEGACY_RELATIONSHIP_PATHS[1],
      keywords: ['关系空间', '关系首页'],
    },
  ]

  const results = buildSearchResults(items, '关系')

  assert.equal(results.filter((item) => item.to === RELATIONSHIP_MANAGEMENT_ROUTE).length, 1)
  assert.ok(results.some((item) => item.to === RELATIONSHIP_LIST_ROUTE))
  assert.ok(results.some((item) => item.to === RELATIONSHIP_INVITE_ROUTE))
  assert.ok(results.some((item) => item.to === RELATIONSHIP_JOIN_ROUTE))

  const managementEntry = results.find((item) => item.to === RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.equal(managementEntry.title, '打开关系总入口')
  assert.match(managementEntry.aliasHint, /我的关系入口|关系空间|关系首页/)
})

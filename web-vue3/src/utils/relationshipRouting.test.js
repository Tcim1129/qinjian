import test from 'node:test'
import assert from 'node:assert/strict'
import {
  LEGACY_RELATIONSHIP_PATHS,
  RELATIONSHIP_INVITE_ROUTE,
  RELATIONSHIP_JOIN_ROUTE,
  RELATIONSHIP_LIST_ROUTE,
  RELATIONSHIP_MANAGEMENT_ROUTE,
  RELATIONSHIP_SPACE_DETAIL_ROUTE_PREFIX,
  RELATIONSHIP_SEARCH_ITEM,
  buildRelationshipSpaceDetailRoute,
  getRelationshipRouteSection,
  normalizeRelationshipPath,
} from './relationshipRouting.js'

test('legacy relationship paths are normalized to the relationship management page', () => {
  assert.deepEqual(LEGACY_RELATIONSHIP_PATHS, ['/pair-waiting', '/relationship-spaces'])
  assert.equal(normalizeRelationshipPath('/pair-waiting'), RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.equal(normalizeRelationshipPath('/relationship-spaces'), RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.equal(normalizeRelationshipPath('/pair'), RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.equal(normalizeRelationshipPath('/profile'), '/profile')
})

test('relationship section routes map to their dedicated sections', () => {
  assert.equal(RELATIONSHIP_LIST_ROUTE, '/pair/list')
  assert.equal(RELATIONSHIP_INVITE_ROUTE, '/pair/invite')
  assert.equal(RELATIONSHIP_JOIN_ROUTE, '/pair/join')
  assert.equal(getRelationshipRouteSection(RELATIONSHIP_LIST_ROUTE, ''), 'pair-list')
  assert.equal(getRelationshipRouteSection(RELATIONSHIP_INVITE_ROUTE, ''), 'pair-create')
  assert.equal(getRelationshipRouteSection(RELATIONSHIP_JOIN_ROUTE, ''), 'pair-join')
  assert.equal(getRelationshipRouteSection(RELATIONSHIP_MANAGEMENT_ROUTE, '#pair-invite'), 'pair-invite')
  assert.equal(getRelationshipRouteSection(RELATIONSHIP_MANAGEMENT_ROUTE, ''), '')
})

test('relationship search item covers switching, inviting, and joining flows', () => {
  assert.equal(RELATIONSHIP_SEARCH_ITEM.to, RELATIONSHIP_MANAGEMENT_ROUTE)
  assert.equal(RELATIONSHIP_SEARCH_ITEM.label, '关系管理')
  assert.match(RELATIONSHIP_SEARCH_ITEM.desc, /切换|邀请|加入/)
  assert.ok(RELATIONSHIP_SEARCH_ITEM.keywords.includes('切换关系'))
  assert.ok(RELATIONSHIP_SEARCH_ITEM.keywords.includes('邀请代码'))
  assert.ok(RELATIONSHIP_SEARCH_ITEM.keywords.includes('建立关系'))
})

test('relationship detail helper builds the dedicated detail route', () => {
  assert.equal(RELATIONSHIP_SPACE_DETAIL_ROUTE_PREFIX, '/relationship-space')
  assert.equal(buildRelationshipSpaceDetailRoute('pair-1'), '/relationship-space/pair-1')
})

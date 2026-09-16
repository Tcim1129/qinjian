export const RELATIONSHIP_MANAGEMENT_ROUTE = '/pair'
export const RELATIONSHIP_LIST_ROUTE = '/pair/list'
export const RELATIONSHIP_INVITE_ROUTE = '/pair/invite'
export const RELATIONSHIP_JOIN_ROUTE = '/pair/join'
export const RELATIONSHIP_SPACE_DETAIL_ROUTE_PREFIX = '/relationship-space'
export const LEGACY_RELATIONSHIP_PATHS = ['/pair-waiting', '/relationship-spaces']

export const RELATIONSHIP_SEARCH_ITEM = {
  label: '关系管理',
  title: '关系管理',
  desc: '查看、邀请、加入都能处理。',
  to: RELATIONSHIP_MANAGEMENT_ROUTE,
  keywords: [
    '关系管理',
    '建立关系',
    '加入关系',
    '切换关系',
    '邀请代码',
    '对方加入',
    '等待加入',
    '关系空间',
  ],
}

export function isLegacyRelationshipPath(path) {
  return LEGACY_RELATIONSHIP_PATHS.includes(String(path || ''))
}

export function normalizeRelationshipPath(path) {
  const normalizedPath = String(path || '')
  if (!normalizedPath) return normalizedPath
  if (normalizedPath === RELATIONSHIP_MANAGEMENT_ROUTE || isLegacyRelationshipPath(normalizedPath)) {
    return RELATIONSHIP_MANAGEMENT_ROUTE
  }
  return normalizedPath
}

export function getRelationshipRouteSection(path, hash = '') {
  const normalizedHash = String(hash || '').replace(/^#/, '')
  if (normalizedHash) return normalizedHash

  switch (String(path || '')) {
    case RELATIONSHIP_LIST_ROUTE:
      return 'pair-list'
    case RELATIONSHIP_INVITE_ROUTE:
      return 'pair-create'
    case RELATIONSHIP_JOIN_ROUTE:
      return 'pair-join'
    default:
      return ''
  }
}

export function buildRelationshipSectionLocation(sectionId, fallbackPath = '') {
  const normalizedSection = String(sectionId || '').replace(/^#/, '').trim()
  if (!normalizedSection) {
    return {
      path: normalizeRelationshipPath(fallbackPath) || RELATIONSHIP_MANAGEMENT_ROUTE,
    }
  }

  switch (normalizedSection) {
    case 'pair-list':
      return { path: RELATIONSHIP_LIST_ROUTE, hash: '#pair-list' }
    case 'pair-create':
      return { path: RELATIONSHIP_INVITE_ROUTE, hash: '#pair-create' }
    case 'pair-join':
      return { path: RELATIONSHIP_JOIN_ROUTE, hash: '#pair-join' }
    default:
      return {
        path: normalizeRelationshipPath(fallbackPath) || RELATIONSHIP_MANAGEMENT_ROUTE,
        hash: `#${normalizedSection}`,
      }
  }
}

export function buildRelationshipSpaceDetailRoute(pairId) {
  return `${RELATIONSHIP_SPACE_DETAIL_ROUTE_PREFIX}/${String(pairId || '').trim()}`
}

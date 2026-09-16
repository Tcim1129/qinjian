import {
  RELATIONSHIP_INVITE_ROUTE,
  RELATIONSHIP_JOIN_ROUTE,
  RELATIONSHIP_LIST_ROUTE,
  RELATIONSHIP_MANAGEMENT_ROUTE,
  normalizeRelationshipPath,
} from './relationshipRouting.js'

export const RELATIONSHIP_PROFILE_ACTIONS = [
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
]

export const RELATIONSHIP_SEARCH_ITEMS = [
  {
    label: '关系',
    title: '查看当前关系',
    desc: '查看或切换当前关系。',
    to: RELATIONSHIP_LIST_ROUTE,
    keywords: [
      '查看关系',
      '当前关系',
      '关系列表',
      '切换关系',
      '已有关系',
      '我的关系',
    ],
  },
  {
    label: '关系',
    title: '发邀请码给对方',
    desc: '创建邀请码，发给对方。',
    to: RELATIONSHIP_INVITE_ROUTE,
    keywords: [
      '发起邀请',
      '建立邀请',
      '关系与邀请',
      '邀请码',
      '邀请代码',
      '建立关系',
      '邀请对方',
    ],
  },
  {
    label: '关系',
    title: '输入收到的邀请码',
    desc: '输入邀请码，加入关系。',
    to: RELATIONSHIP_JOIN_ROUTE,
    keywords: [
      '输入邀请码',
      '加入关系',
      '加入邀请',
      '填写邀请码',
      '邀请码',
      '邀请代码',
      '关系与邀请',
    ],
  },
  {
    label: '关系',
    title: '打开关系总入口',
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
      '关系入口',
      '关系首页',
    ],
  },
]

function normalizeSearchText(value) {
  return String(value || '').trim().toLowerCase()
}

function uniqueSearchTexts(values) {
  const seen = new Set()
  return values.reduce((result, value) => {
    const text = String(value || '').trim()
    const normalized = normalizeSearchText(text)
    if (!normalized || seen.has(normalized)) return result
    seen.add(normalized)
    result.push(text)
    return result
  }, [])
}

function getSearchItemKeywords(item) {
  return uniqueSearchTexts([item?.label, item?.title, ...(Array.isArray(item?.keywords) ? item.keywords : [])])
}

export function getSearchItemKey(item) {
  const customKey = String(item?.searchKey || '').trim()
  if (customKey) return normalizeSearchText(customKey)
  const path = normalizeRelationshipPath(item?.to) || String(item?.to || '').trim()
  return normalizeSearchText(path)
}

export function buildSearchResults(items, query) {
  const normalizedQuery = normalizeSearchText(query)
  if (!normalizedQuery) return []

  const results = []
  const resultsByKey = new Map()

  items.forEach((item) => {
    const keywords = getSearchItemKeywords(item)
    const terms = uniqueSearchTexts([...keywords, item?.desc])
    const hasMatch = terms.some((term) => normalizeSearchText(term).includes(normalizedQuery))
    if (!hasMatch) return

    const key = getSearchItemKey(item) || `search-item-${results.length}`
    const normalizedPath = normalizeRelationshipPath(item?.to) || item?.to

    if (!resultsByKey.has(key)) {
      const nextItem = {
        ...item,
        to: normalizedPath,
        aliases: keywords,
        mergedAliases: [],
        mergedCount: 1,
      }
      resultsByKey.set(key, nextItem)
      results.push(nextItem)
      return
    }

    const current = resultsByKey.get(key)
    current.aliases = uniqueSearchTexts([...current.aliases, ...keywords])
    current.mergedAliases = uniqueSearchTexts([...current.mergedAliases, ...keywords])
    current.mergedCount += 1
    if (!current.desc && item?.desc) {
      current.desc = item.desc
    }
  })

  return results.map((item) => {
    const aliasHint = item.mergedCount > 1 ? uniqueSearchTexts(item.mergedAliases).filter((value) => {
      const normalizedValue = normalizeSearchText(value)
      return normalizedValue
        && normalizedValue !== normalizeSearchText(item.title)
        && normalizedValue !== normalizeSearchText(item.label)
    }).slice(0, 3).join(' / ') : ''

    return {
      ...item,
      aliasHint,
    }
  })
}

export function getRelationshipSearchItems() {
  return RELATIONSHIP_SEARCH_ITEMS
}

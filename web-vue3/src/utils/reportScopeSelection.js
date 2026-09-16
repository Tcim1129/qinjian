function normalizeId(value) {
  return String(value || '').trim()
}

function extractPairId(item) {
  if (typeof item === 'string') return normalizeId(item)
  return normalizeId(item?.pair_id || item?.id)
}

export function resolveScopedPairId({ preferredPairId = '', fallbackPairId = '', availablePairs = [] } = {}) {
  const availableIds = availablePairs
    .map(extractPairId)
    .filter(Boolean)

  if (!availableIds.length) return ''

  const preferredId = normalizeId(preferredPairId)
  if (preferredId && availableIds.includes(preferredId)) return preferredId

  const fallbackId = normalizeId(fallbackPairId)
  if (fallbackId && availableIds.includes(fallbackId)) return fallbackId

  return availableIds[0] || ''
}

export function buildPairQuery(pairId) {
  const normalized = normalizeId(pairId)
  return normalized ? { pair_id: normalized } : {}
}

export function resolveRelationshipSelection({ nextPairId, focusPairId = '' } = {}) {
  const normalizedPairId = String(nextPairId || '')
  if (!normalizedPairId) {
    return {
      selectedPairId: '',
      focusPairId,
    }
  }

  if (normalizedPairId === '__overflow__') {
    return {
      selectedPairId: '__overflow__',
      focusPairId: '',
    }
  }

  return {
    selectedPairId: normalizedPairId,
    focusPairId: focusPairId === normalizedPairId ? '' : normalizedPairId,
  }
}

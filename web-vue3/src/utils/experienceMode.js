function normalizeId(value) {
  return String(value || '').trim()
}

function findActivePairId(pairs) {
  if (!Array.isArray(pairs)) return ''
  const active = pairs.find((pair) => pair?.status === 'active' && normalizeId(pair.id))
  return normalizeId(active?.id)
}

export function resolveExperienceMode({
  isDemoMode = false,
  activePairId = '',
  currentPair = null,
  pairs = [],
  testingUnrestricted = false,
} = {}) {
  const explicitActivePairId = normalizeId(activePairId)
  const currentActivePairId =
    currentPair?.status === 'active' ? normalizeId(currentPair.id) : ''
  const resolvedActivePairId =
    explicitActivePairId || currentActivePairId || findActivePairId(pairs)
  const hasPairContext = Boolean(resolvedActivePairId)
  const canBypassFeatureGates = Boolean(testingUnrestricted) && !isDemoMode

  return {
    isDemoMode: Boolean(isDemoMode),
    isSampleOnly: Boolean(isDemoMode),
    testingUnrestricted: Boolean(testingUnrestricted),
    canBypassFeatureGates,
    dataMode: isDemoMode ? 'demo' : 'real',
    executionMode: isDemoMode ? 'sample-only' : 'online',
    relationshipScope: hasPairContext ? 'pair' : 'solo',
    activePairId: resolvedActivePairId,
    hasPairContext,
    isPairExperience: hasPairContext,
    isSoloExperience: !hasPairContext,
    isRealSoloExperience: !isDemoMode && !hasPairContext,
    canUseOnlineAi: !isDemoMode,
    canUseVoice: !isDemoMode,
    canUseDualPerspective: hasPairContext,
    canUseRelationshipContext: hasPairContext,
    canUseMultiRelationship: Array.isArray(pairs)
      ? pairs.filter((pair) => pair?.status === 'active').length > 1
      : false,
  }
}

export function featureUnavailableReason(feature, mode) {
  const normalizedFeature = String(feature || '').trim()
  const resolvedMode = mode || resolveExperienceMode()

  if (normalizedFeature === 'demo-online') {
    return '样例模式暂不做真实整理。'
  }
  if (normalizedFeature === 'voice') {
    return resolvedMode.isDemoMode
      ? '样例模式暂不能用语音。'
      : '现在暂不能用语音。'
  }
  if (normalizedFeature === 'dual-perspective') {
    return '双方都留下记录后才能看双视角。'
  }
  if (normalizedFeature === 'pair-context') {
    return resolvedMode.isDemoMode
      ? '样例模式只展示样例关系。'
      : '需要先建立具体关系。'
  }
  return resolvedMode.isDemoMode
    ? '样例模式只展示样例。'
    : '现在暂不能用。'
}

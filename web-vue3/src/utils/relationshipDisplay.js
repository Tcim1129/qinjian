export function resolveRelationshipDisplayPair({
  activePair = null,
  currentPair = null,
} = {}) {
  return activePair || currentPair || null
}

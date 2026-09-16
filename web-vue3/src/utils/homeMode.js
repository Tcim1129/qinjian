import { relationshipTypeLabel } from './displayText.js'

function normalizePartnerName(value) {
  const text = String(value || '').trim()
  return text || '对方'
}

export function resolveHomeRelationshipView({ currentPair = null, partnerName = '' } = {}) {
  if (currentPair?.status === 'active') {
    return {
      kind: 'paired',
      sectionLabel: '现在这段关系',
      relationLabel: `${relationshipTypeLabel(currentPair.type)} · ${normalizePartnerName(partnerName)}`,
      partnerMetricLabel: '对方状态',
      signalMetricLabel: '关系信号',
      showRelationshipTree: true,
      sideCardTitle: '',
    }
  }

  if (currentPair?.status === 'pending') {
    return {
      kind: 'pending',
      sectionLabel: '当前状态',
      relationLabel: `${relationshipTypeLabel(currentPair.type)} · 等待加入`,
      partnerMetricLabel: '当前邀请',
      signalMetricLabel: '整理节奏',
      showRelationshipTree: false,
      sideCardTitle: '先发邀请，再开始',
    }
  }

  return {
    kind: 'solo',
    sectionLabel: '当前模式',
    relationLabel: '单人整理',
    partnerMetricLabel: '当前状态',
    signalMetricLabel: '整理节奏',
    showRelationshipTree: false,
    sideCardTitle: '先自己记下来',
  }
}

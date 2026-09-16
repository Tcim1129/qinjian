import { pairStatusLabel, relationshipTypeLabel } from './displayText.js'

function normalizeDisplayName(value, fallback) {
  const text = String(value || '').trim()
  return text || fallback
}

function getPartnerDisplayName(pair) {
  return normalizeDisplayName(
    pair?.custom_partner_nickname || pair?.partner_nickname || pair?.partner_email || pair?.partner_phone,
    pair?.status === 'active' ? '对方' : '等待加入',
  )
}

function buildMoments(pair) {
  if (pair?.status === 'active') {
    return [
      '首页、记录、简报已切到这段关系。',
      '记录单独保存。',
      '可继续管理其他关系。',
    ]
  }

  return [
    '邀请码已准备。',
    '加入前可继续单人记录。',
    '加入后进入双人空间。',
  ]
}

export function buildRelationshipSpaces({ pairs = [], me = null } = {}) {
  const myName = normalizeDisplayName(me?.nickname, '我')

  return pairs.map((pair) => {
    const partnerName = getPartnerDisplayName(pair)
    const active = pair?.status === 'active'

    return {
      id: pair.id,
      pair_id: pair.id,
      type: relationshipTypeLabel(pair?.type),
      title: partnerName,
      tree_stage: pairStatusLabel(pair?.status),
      people: active ? [myName, partnerName] : [myName, '等待加入'],
      status: active ? '这段关系正在记录中' : '这段关系还在等待加入',
      prompt: active
        ? '单独记录。'
        : '等待邀请码。',
      signal: active ? '已建立' : '待加入',
      moments: buildMoments(pair),
    }
  })
}

export { getPartnerDisplayName }

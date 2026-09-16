import { pairStatusLabel, relationshipTypeLabel } from './displayText.js'

export const PAIR_CHANGE_KIND_LABELS = {
  join_request: '加入关系',
  type_change: '切换关系类型',
  break_request: '移除关系',
}

export function pairChangeKindLabel(value) {
  return PAIR_CHANGE_KIND_LABELS[String(value || '').trim()] || '关系确认'
}

export function isPairChangeWaitingForMe(request, meId) {
  return Boolean(request?.waiting_for_me || (meId && String(request?.approver_user_id || '') === String(meId)))
}

export function isPairChangeRequestedByMe(request, meId) {
  return Boolean(request?.requested_by_me || (meId && String(request?.requester_user_id || '') === String(meId)))
}

export function isBreakRequest(request) {
  return String(request?.kind || '') === 'break_request'
}

export function breakRequestPhaseLabel(phase) {
  const normalized = String(phase || '').trim()
  if (normalized === 'awaiting_timeout') return '倒计时中'
  if (normalized === 'awaiting_retention_choice') return '待对方选择'
  if (normalized === 'retaining') return '挽留中'
  return '处理中'
}

export function describePairChangeRequest(request) {
  if (!request) return ''
  const kind = String(request.kind || '')
  const requestedType = relationshipTypeLabel(request.requested_type)
  const requester = String(request.requester_nickname || '对方').trim()

  if (kind === 'join_request') {
    return `${requester} 希望按“${requestedType}”建立这段关系`
  }

  if (kind === 'type_change') {
    return `${requester} 希望把关系切换成“${requestedType}”`
  }

  if (kind === 'break_request') {
    if (request.phase === 'awaiting_timeout') {
      return `${requester} 发起了移除关系申请，这段关系会在 24 小时后自动解除`
    }
    if (request.phase === 'awaiting_retention_choice') {
      return `${requester} 发起了移除关系申请，正在等待对方决定是否挽留`
    }
    if (request.phase === 'retaining') {
      return `${requester} 发起的移除关系申请已进入挽留阶段，正在等待最终决定`
    }
    return `${requester} 发起了一次移除关系申请`
  }

  return `${requester} 发起了一次${pairChangeKindLabel(kind)}`
}

export function describePairChangeResult(request) {
  if (!request || request.status === 'pending') return ''
  const status = pairStatusLabel(request.status)
  const requestedType = relationshipTypeLabel(request.requested_type)
  const kind = String(request.kind || '')

  if (kind === 'join_request') {
    return `最近一次加入请求${status}${request.status === 'approved' ? `，已按“${requestedType}”建立` : ''}`
  }

  if (kind === 'type_change') {
    return `最近一次类型切换${status}${request.status === 'approved' ? `，当前按“${requestedType}”处理` : ''}`
  }

  if (kind === 'break_request') {
    const reason = String(request.resolution_reason || '').trim()
    if (request.status === 'rejected' && reason === 'retention_accepted') {
      return '最近一次移除关系申请已被接受挽留，关系恢复正常'
    }
    if (request.status === 'cancelled') {
      return '最近一次移除关系申请已被发起方撤回'
    }
    if (reason === 'no_retention_timeout') {
      return '最近一次移除关系申请已按 24 小时倒计时自动生效，关系已解除'
    }
    if (reason === 'partner_declined') {
      return '最近一次移除关系申请已由对方选择不挽留，关系已解除'
    }
    if (reason === 'choice_timeout') {
      return '最近一次移除关系申请因对方超时未回应，关系已自动解除'
    }
    if (reason === 'retention_rejected') {
      return '最近一次移除关系申请在挽留后仍被拒绝，关系已解除'
    }
    if (reason === 'retention_timeout') {
      return '最近一次移除关系申请在挽留阶段超时，关系已自动解除'
    }
    return `最近一次移除关系申请${status}`
  }

  return `最近一次${pairChangeKindLabel(kind)}${status}`
}

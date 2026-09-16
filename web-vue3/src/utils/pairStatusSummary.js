import { pairStatusLabel, relationshipTypeLabel } from './displayText.js'
import { getPartnerDisplayName } from './relationshipSpaces.js'

const TREND_LABELS = {
  up: '在变好',
  down: '有点紧',
  flat: '比较稳定',
}

const SUMMARY_COPY = {
  pending: {
    summary: '等待对方加入。',
    nextAction: '发送邀请码。',
  },
  active: {
    summary: '关系已建立。',
    nextAction: '先做一个小动作。',
  },
  ended: {
    summary: '关系已结束。',
    nextAction: '回到关系管理。',
  },
}

function normalizeTrend(value) {
  const trend = String(value || 'flat').trim().toLowerCase()
  return trend === 'up' || trend === 'down' ? trend : 'flat'
}

function normalizeScore(value) {
  if (value === null || value === undefined || value === '') return null
  const score = Number(value)
  return Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : null
}

function buildFallbackSummary(pair, trend, isCurrent) {
  if (trend === 'up') return '回应更顺。'
  if (trend === 'down') return '最近有点卡。'

  if (pair?.status === 'active') {
    return isCurrent
      ? '已建立。'
      : '已经建立。点开查看。'
  }

  const statusCopy = SUMMARY_COPY[pair?.status] || SUMMARY_COPY.pending
  return statusCopy.summary
}

function buildFallbackNextAction(pair, isCurrent) {
  if (pair?.status === 'active') {
    return isCurrent
      ? '去记录或关系日历看看。'
      : '打开专属关系页。'
  }

  const statusCopy = SUMMARY_COPY[pair?.status] || SUMMARY_COPY.pending
  return statusCopy.nextAction
}

function buildFallbackTrendLabel(pair, isCurrent, hasScore) {
  if (hasScore) return ''
  if (pair?.status === 'pending') return '等待加入'
  if (pair?.status === 'active') return isCurrent ? '等真实记录' : ''
  return '待补充'
}

function buildFallbackInviteMode(pair, inviteCode) {
  if (!inviteCode) return 'none'
  return pair?.status === 'pending' ? 'pending' : 'active'
}

function buildFallbackInviteNote(inviteMode) {
  if (inviteMode === 'pending') return '等待对方加入。'
  if (inviteMode === 'active') return '关系已建立。'
  return ''
}

function buildPendingBreakSummary(request, pair) {
  if (request?.phase === 'awaiting_timeout') {
    return {
      summary: '这段关系已进入移除倒计时，24 小时后会自动解除。',
      nextAction: '打开专属关系页。',
      scoreLabel: '倒计时中',
      trendLabel: '移除流程中',
    }
  }

  if (request?.phase === 'awaiting_retention_choice') {
    return {
      summary: '等待对方决定是否挽留。',
      nextAction: '打开专属关系页。',
      scoreLabel: '待对方决定',
      trendLabel: '移除流程中',
    }
  }

  if (request?.phase === 'retaining') {
    return {
      summary: '挽留阶段进行中。',
      nextAction: '打开专属关系页。',
      scoreLabel: '挽留中',
      trendLabel: '移除流程中',
    }
  }

  return {
    summary: pair?.status === 'active' ? '有待处理申请。' : '处理中。',
    nextAction: '打开专属关系页。',
    scoreLabel: '处理中',
    trendLabel: '移除流程中',
  }
}

export function buildPairStatusSummary({ pair, metric, label, isCurrent = false, inviteCode = '' } = {}) {
  const trend = normalizeTrend(metric?.trend)
  const score = normalizeScore(metric?.score)
  const hasScore = score !== null
  const resolvedInviteCode = String(inviteCode || metric?.inviteCode || '').trim()
  const inviteMode = String(metric?.inviteMode || '').trim() || buildFallbackInviteMode(pair, resolvedInviteCode)
  const pendingBreakRequest = pair?.pending_change_request?.kind === 'break_request'
    ? pair.pending_change_request
    : null
  const title = String(label || metric?.title || '').trim() || getPartnerDisplayName(pair)
  const typeLabel = relationshipTypeLabel(pair?.type)
  const statusLabel = pairStatusLabel(pair?.status)
  const pendingBreakSummary = pendingBreakRequest ? buildPendingBreakSummary(pendingBreakRequest, pair) : null
  const summary = pendingBreakSummary?.summary
    || String(metric?.summary || '').trim()
    || buildFallbackSummary(pair, trend, isCurrent)
  const nextAction = pendingBreakSummary?.nextAction
    || String(metric?.nextAction || '').trim()
    || buildFallbackNextAction(pair, isCurrent)
  const scoreHeading = String(metric?.scoreHeading || '').trim() || (hasScore ? '关系评分' : '当前状态')
  const scoreLabel = pendingBreakSummary?.scoreLabel
    || String(metric?.scoreLabel || '').trim() || (
    hasScore
      ? String(score)
      : pair?.status === 'pending'
        ? '待加入'
        : statusLabel
  )
  const trendLabel = pendingBreakSummary?.trendLabel
    || String(metric?.trendLabel || '').trim()
    || (hasScore ? (TREND_LABELS[trend] || TREND_LABELS.flat) : buildFallbackTrendLabel(pair, isCurrent, hasScore))
  const inviteNote = String(metric?.inviteNote || '').trim() || buildFallbackInviteNote(inviteMode)

  return {
    pairId: pair?.id || '',
    title,
    typeLabel,
    statusLabel,
    score,
    scoreLabel,
    scoreHeading,
    hasScore,
    trend,
    trendLabel,
    summary,
    recentSummary: summary,
    nextAction,
    inviteCode: resolvedInviteCode,
    inviteMode,
    inviteNote,
  }
}

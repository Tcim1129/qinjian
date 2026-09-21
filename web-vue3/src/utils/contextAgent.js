export function buildContextPrompt(context = {}) {
  const source = String(context.sourceLabel || '当前记录').trim().slice(0, 100)
  const summary = String(context.summary || '').trim().slice(0, 3200)
  const question = String(context.question || '请帮我梳理这件事，看看下一步可以怎么做。').trim().slice(0, 600)
  return `${source}\n\n${summary}\n\n${question}\n\n请把事实和推测分开，不确定的地方直接说明。推测不代表对方真实想法。先给建议，不要保存记录或创建任务。`
}

export function buildSceneContext(context = {}) {
  return {
    source_label: String(context.sourceLabel || '当前记录').trim().slice(0, 100),
    summary: String(context.summary || '').trim().slice(0, 3200),
    intent: ['auto', 'listen', 'wording', 'plan', 'reflect'].includes(context.intent) ? context.intent : 'auto',
  }
}

const toolLabels = {
  get_relationship_status: '查看关系近况', get_recent_events: '查看近期记录',
  search_timeline: '查找相关往事', get_active_tasks: '查看已有安排',
  get_task_feedback: '查看之前的反馈', get_crisis_status: '检查安全提醒',
  analyze_behavior: '梳理当前表达', preview_message_risk: '检查这句话的表达',
  evaluate_intervention_need: '评估下一步', create_task: '提出行动建议',
  extract_checkin_data: '整理记录内容',
}

export function summarizeAgentTools(trace = []) {
  return trace.flatMap((step, index) => (step.tool_results || []).map((item, itemIndex) => {
    const result = item.result || {}
    const status = result.status === 'success' ? 'success' : result.status === 'error' ? 'error' : 'unknown'
    return {
      key: `${index}-${itemIndex}`, label: toolLabels[item.name] || '其他操作', status,
      summary: status === 'error' ? '这一步没有完成' : status !== 'success' ? '暂无完成结果'
        : item.name === 'create_task' ? '仅生成建议，保存仍需你确认'
          : Array.isArray(result.data) ? `返回 ${result.data.length} 条可用结果` : '已返回结果',
    }
  })).slice(0, 12)
}

export function isContextScopeCurrent(context, activePairId) {
  return String(context?.pairId || '') === String(activePairId || '')
}

export function isChatScopeCurrent(snapshot, current) {
  return !current.disposed && ['token', 'userId', 'pairId', 'revision'].every(key => String(snapshot[key] || '') === String(current[key] || ''))
}

export function isContextScopeAvailable(context, activePairId, pairs = []) {
  const id = String(context?.pairId || '')
  if (!id) return isContextScopeCurrent(context, activePairId)
  return pairs.some(pair => String(pair.id) === id && pair.status === 'active')
}

export function buildAlignmentContext(alignment, kind = 'compare', { pairId = null, isDemoMode = false, myLabel = '', partnerLabel = '', mySummary = '', partnerSummary = '' } = {}) {
  const perspectives = [
    mySummary
      ? `我（${myLabel || alignment.user_a_label || '我'}）：${mySummary}`
      : (alignment.user_a_label || '成员 A') + '：' + (alignment.view_a_summary || '暂无摘要'),
    partnerSummary
      ? `对方（${partnerLabel || alignment.user_b_label || '对方'}）：${partnerSummary}`
      : (alignment.user_b_label || '成员 B') + '：' + (alignment.view_b_summary || '暂无摘要'),
    alignment.shared_story ? '已有分析：' + alignment.shared_story : '',
  ].filter(Boolean)
  const options = {
    compare: ['聊聊双方的看法', '我们是不是误会了什么？'],
    opening: ['换个说法', '帮我把这句话说得自然一点，保留我的意思。'],
    action: ['商量下一步', '这几件事里，哪件现在比较容易做？'],
  }
  const [title, question] = options[kind] || options.compare
  if (kind === 'opening' && alignment.suggested_opening) perspectives.push('待修改的开场白：' + alignment.suggested_opening)
  if (kind === 'action' && Array.isArray(alignment.bridge_actions)) perspectives.push('已有建议：\n' + alignment.bridge_actions.join('\n'))
  return { title, sourceLabel: (alignment.checkin_date || '最近一次') + ' · 双视角' + (isDemoMode ? ' · 样例' : ''), summary: perspectives.join('\n'), question, pairId, intent: kind === 'opening' ? 'wording' : kind === 'action' ? 'plan' : 'reflect' }
}

const dayKey = value => String(value || '').slice(0, 10)
function dateOf(value) {
  const key = dayKey(value)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) return null
  const date = new Date(`${key}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? null : date
}
const iso = date => date.toISOString().slice(0, 10)
const shift = (date, days) => new Date(date.getTime() + days * 86400000)
const chineseDate = date => `${date.getUTCFullYear()}年${date.getUTCMonth() + 1}月${date.getUTCDate()}日`

export function reportPeriodLabel(report = {}) {
  const end = dateOf(report.report_date || report.created_at)
  if (!end) return ''
  const days = { weekly: 7, monthly: 30 }[report.report_type || report.type]
  // The backend selects records from report_date minus 7/30 days, inclusively.
  return days ? `${chineseDate(shift(end, -days))}–${chineseDate(end)}` : chineseDate(end)
}

export function selectReportHistory(rows = [], type = 'daily') {
  const seen = new Set()
  return [...rows]
    .filter(row => (row.report_type || row.type || type) === type)
    .sort((a, b) => String(b.report_date || b.created_at || '').localeCompare(String(a.report_date || a.created_at || '')) || String(b.created_at || '').localeCompare(String(a.created_at || '')))
    .filter(row => {
      const key = dayKey(row.report_date || row.created_at) || row.id
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

// Sample-only narratives and values. Never fill gaps in a real report with these.
export function buildSampleReports(base, type = 'daily') {
  const step = { daily: 1, weekly: 7, monthly: 30 }[type] || 1
  const name = base.scope_name || '对方'
  const stories = {
    daily: [
      [`今天和${name}聊得比前两天轻松一些。`, '你们聊到了各自的近况，也给对方留了说话的时间。', '下次联系时，可以接着问问今天没聊完的那件事。'],
      [`今天想联系${name}，但一直没找到合适的时间。`, '今天的联系比较少，还不能据此判断对方的态度。', '先问一句什么时候方便，不急着把所有话一次说完。'],
      [`今天和${name}聊天时，有一句话没说清楚。`, '你想表达关心，但对方可能听成了催促，还需要确认。', '可以补一句“我不是催你，只是想知道你最近怎么样”。'],
    ],
    weekly: [
      [`这一周，和${name}的联系慢慢恢复了。`, '前几天错开的聊天，后来找到了双方都方便的时间。', '下一周先留一个能好好聊聊的时间，不必每天都安排任务。'],
      [`上一周，和${name}常常没能赶上同一个空闲时间。`, '几次没聊成主要和时间有关，不等于彼此不在意。', '先商量一个双方方便的时间，临时有事也可以改。'],
      [`这一周，和${name}有过一次没说开的分歧。`, '后来虽然恢复了联系，但那次分歧还没有聊清楚。', '等双方都愿意时，只聊那一件事，先听完再回应。'],
    ],
    monthly: [
      [`这一个月，和${name}逐渐找到了更舒服的相处节奏。`, '从总想立刻得到回应，到能提前说一声自己什么时候有空。', '把有效的做法留下来，不用因为进展顺利就增加安排。'],
      [`这一个月，和${name}的联系时多时少。`, '忙碌时容易把少联系理解为疏远，但记录里也有主动关心。', '一起商量忙的时候怎么打个招呼，不要求随时回复。'],
      [`这一个月，和${name}还在摸索彼此能接受的沟通方式。`, '遇到分歧时，你们有时会急着解释，反而没听清对方。', '下次有分歧，先确认自己有没有听懂，再讲自己的想法。'],
    ],
  }[type] || []
  return stories.map(([summary, insight, action], index) => {
    const end = shift(dateOf('2026-03-21'), -index * step)
    const score = Math.max(0, Math.min(100, Number(base.health_score ?? 84) - index * 4))
    return {
      ...base, id: `${base.pair_id}-${type}-${iso(end)}`, report_type: type,
      report_date: iso(end), created_at: `${iso(end)}T22:00:00Z`, status: 'completed',
      health_score: score, score_label: '样例评分', summary, nextAction: action,
      insights: [insight], recommendations: [action], tags: ['样例'],
      dimensions: (base.dimensions || []).map(axis => ({ ...axis, score: Math.max(0, Math.min(100, axis.score - index * 4)) })),
      trend_points: Array.from({ length: 6 }, (_, i) => ({ date: iso(shift(end, i - 5)), score: Math.max(0, score - [12, 8, 10, 3, 1, 0][i]) })),
    }
  })
}

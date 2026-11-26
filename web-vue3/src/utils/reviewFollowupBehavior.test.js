import test from 'node:test'
import assert from 'node:assert/strict'
import { extractReportSummary, extractReportInsights, extractReportRecommendations, extractStructuredReportDimensions } from './reportContent.js'
import { selectReportHistory } from './reportPeriods.js'
import { shouldShowReactionShift } from './displayText.js'

test('personal report displays its own summary, emotional pattern and care suggestion', () => {
  const report = { type: 'solo', content: { self_insight: '今天累了也愿意照顾自己。', emotional_pattern: '忙完后需要安静一会儿。', relationship_note: '不用催着自己立刻回应。', self_care_tip: '先散步十分钟。' } }
  assert.equal(extractReportSummary(report), report.content.self_insight)
  assert.deepEqual(extractReportInsights(report), [report.content.emotional_pattern, report.content.relationship_note])
  assert.deepEqual(extractReportRecommendations(report), [report.content.self_care_tip])
})

test('daily radar uses the declared ten and hundred point scales even at low scores', () => {
  const report = { content: { communication_quality: { score: 6 }, emotional_sync: { score: 5 }, interaction_balance: { score: 8 }, mood_a: { score: 7 }, mood_b: { score: 3 } } }
  const scores = Object.fromEntries(extractStructuredReportDimensions(report).map(x => [x.id, x.score]))
  assert.deepEqual(scores, { communication_quality: 60, emotional_sync: 5, interaction_balance: 8, mood_a: 70, mood_b: 30 })
})

test('daily and personal report histories remain distinct when both are present', () => {
  const rows = [{ id: 'pair', type: 'daily', report_date: '2026-11-26' }, { id: 'self', type: 'solo', report_date: '2026-11-25' }]
  assert.deepEqual(selectReportHistory(rows, 'daily').map(x => x.id), ['pair'])
  assert.deepEqual(selectReportHistory(rows, 'solo').map(x => x.id), ['self'])
})

test('missing radar inputs do not become fabricated zero values', () => {
  assert.deepEqual(extractStructuredReportDimensions({ content: { communication_quality: true, emotional_sync: ' ', interaction_balance: null, mood_a: false } }), [])
})

test('stable reaction copy never contradicts a detected baseline deviation', () => {
  for (const baseline_match of ['slight_deviation', 'strong_deviation']) {
    assert.equal(shouldShowReactionShift({ baseline_match, reaction_shift: 'stable' }), false)
    assert.equal(shouldShowReactionShift({ baseline_match, reaction_shift: 'defensive' }), true)
  }
  assert.equal(shouldShowReactionShift({ baseline_match: 'match', reaction_shift: 'stable' }), true)
  assert.equal(shouldShowReactionShift({ reaction_shift: 'unknown' }), false)
  assert.equal(shouldShowReactionShift(null), false)
})

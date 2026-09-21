import test from 'node:test'
import assert from 'node:assert/strict'
import { buildSceneContext, summarizeAgentTools } from './contextAgent.js'
import * as schedule from './taskSchedule.js'
const { buildTaskFollowupContext, feedbackPayload } = schedule

test('scene requests separate the editable question from bounded visible references', () => {
  const result = buildSceneContext({ sourceLabel: '今日记录', summary: '约定取消了', intent: 'wording', pairId: 'a', secret: 'HIDDEN' })
  assert.deepEqual(result, { source_label: '今日记录', summary: '约定取消了', intent: 'wording' })
  assert.equal(buildSceneContext({ summary: '字'.repeat(9000), intent: 'root' }).summary.length, 3200)
  assert.equal(buildSceneContext({ intent: 'root' }).intent, 'auto')
})

test('feedback does not turn unanswered ratings into zero and rejects empty feedback', () => {
  assert.equal(feedbackPayload({}), null)
  assert.deepEqual(feedbackPayload({ outcome: 'not_yet', note: ' 忙 ', usefulness_score: null }), {
    outcome: 'not_yet', note: '忙', usefulness_score: null, friction_score: null, relationship_shift_score: null,
  })
  assert.equal(feedbackPayload({ outcome: 'made-up' }), null)
})

test('a written result is useful feedback even without selecting an outcome or rating', () => {
  assert.deepEqual(feedbackPayload({ note: '  聊了一会儿，还不确定有没有帮助  ' }), {
    outcome: null, note: '聊了一会儿，还不确定有没有帮助', usefulness_score: null, friction_score: null, relationship_shift_score: null,
  })
  assert.equal(feedbackPayload({ note: '  ' }), null)
})

test('completion is not a positive outcome, and state changes discard incompatible old ratings', () => {
  assert.equal(schedule.buildTaskResultFeedback({ status: 'pending' }, { status: 'completed' }), null)
  const original = { status: 'completed', feedback: { outcome: 'helped', usefulness_score: 4, friction_score: 2, note: '聊开了' } }
  assert.deepEqual(schedule.buildTaskResultFeedback(original, { status: 'completed', outcome: 'helped', note: '补充了时间' }), {
    outcome: 'helped', note: '补充了时间', usefulness_score: 4, friction_score: 2, relationship_shift_score: null,
  })
  const pending = schedule.buildTaskResultFeedback(original, { status: 'pending', outcome: 'helped', note: '记错了，还没做' })
  assert.equal(pending.outcome, 'not_yet')
  assert.equal(pending.usefulness_score, null)
  assert.equal(schedule.buildTaskResultFeedback(original, { status: 'completed', outcome: 'uncertain', note: '重新想了想' }).usefulness_score, null)
  assert.equal(original.feedback.usefulness_score, 4)
})

test('uncertain outcomes remain uncertain and followup does not assume a failure', () => {
  const feedback = schedule.buildTaskResultFeedback({ status: 'pending' }, { status: 'completed', outcome: 'uncertain', note: '' })
  assert.equal(feedback.outcome, 'uncertain')
  const context = schedule.buildTaskResultContext({ title: '一起散步', status: 'completed', feedback }, { date: '2026-09-09', pairId: 'p' })
  assert.equal(context.pairId, 'p')
  assert.match(context.summary, /已完成/)
  assert.match(context.summary, /还说不准/)
  assert.ok(!context.summary.includes('有帮助'))
})

test('next day discussion carries the actual outcome and date without inventing results', () => {
  const context = buildTaskFollowupContext({ title: '聊十分钟', status: 'pending', feedback: { outcome: 'not_yet', note: '今天没空' } }, { pairId: 'a', now: new Date(2026, 11, 31) })
  assert.equal(context.pairId, 'a')
  assert.equal(context.intent, 'plan')
  assert.ok(context.sourceLabel.includes('2027-01-01'))
  assert.ok(context.summary.includes('今天没空'))
  assert.ok(context.summary.includes('未完成'))
  assert.ok(!context.summary.includes('0/5'))
})

test('tool summaries expose observed operations but not raw thoughts, arguments or failed success', () => {
  const results = summarizeAgentTools([{ thought: 'PRIVATE THOUGHT', tool_calls: [{ function: { name: 'get_recent_events', arguments: 'SECRET' } }], tool_results: [
    { name: 'get_recent_events', result: { status: 'success', data: [{ id: 'one', text: 'PRIVATE RECORD' }] } },
    { name: 'create_task', result: { status: 'error', message: 'DB SECRET' } },
  ] }])
  assert.equal(results.length, 2)
  assert.equal(results[0].status, 'success')
  assert.equal(results[1].status, 'error')
  assert.ok(!JSON.stringify(results).includes('PRIVATE'))
  assert.ok(!JSON.stringify(results).includes('SECRET'))
})

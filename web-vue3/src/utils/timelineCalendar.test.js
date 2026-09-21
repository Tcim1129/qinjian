import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildCalendarDays,
  mergeTimelineItems,
  timelineBusinessDateKey,
} from './timelineCalendar.js'

test('无时区时间按 UTC 解释后归入北京时间业务日', () => {
  assert.equal(timelineBusinessDateKey('2026-03-21T20:40:00'), '2026-03-22')
  assert.equal(timelineBusinessDateKey('2026-03-21T20:40:00Z'), '2026-03-22')
})

test('日期型业务日不会被再次按时区平移', () => {
  assert.equal(timelineBusinessDateKey('2026-03-21'), '2026-03-21')
  assert.equal(timelineBusinessDateKey({ local_date: '2026-03-20', occurred_at: '2026-03-21T20:40:00' }), '2026-03-20')
})

test('月历包含完整周并把记录数放到对应日期', () => {
  const days = buildCalendarDays(2026, 2, new Map([
    ['2026-03-01', [{ id: 'a' }]],
    ['2026-03-31', [{ id: 'b' }, { id: 'c' }]],
  ]), '2026-03-21')

  assert.equal(days.length % 7, 0)
  assert.equal(days[0].key, '2026-03-01')
  assert.equal(days.at(-1).key, '2026-04-04')
  assert.equal(days.find((day) => day.key === '2026-03-31').eventCount, 2)
  assert.equal(days.find((day) => day.key === '2026-03-21').isToday, true)
})

test('事件和档案以业务实体去重并保留详情能力更强的事件', () => {
  const merged = mergeTimelineItems(
    [{ id: 'event-1', entity_type: 'checkin', entity_id: 'record-1', occurred_at: '2026-03-21T10:00:00' }],
    [
      { id: 'record-1', item_type: 'record', occurred_at: '2026-03-21T10:00:00', local_date: '2026-03-21' },
      { id: 'record-2', item_type: 'report', occurred_at: '2026-03-20T10:00:00', local_date: '2026-03-20' },
    ],
  )

  assert.equal(merged.length, 2)
  assert.equal(merged[0].id, 'event-1')
  assert.equal(merged[0].source, 'event')
  assert.equal(merged[1].source, 'archive')
})

test('合并事件与档案时保留业务日期，避免补记被放进提交当天', () => {
  const merged = mergeTimelineItems(
    [{ id: 'event-a', entity_type: 'checkin', entity_id: 'a', occurred_at: '2026-03-23T01:00:00' }],
    [{ id: 'a', item_type: 'record', local_date: '2026-03-20', occurred_at: '2026-03-23T01:00:00', record: { content: '本人原文' } }],
  )
  assert.equal(merged.length, 1)
  assert.equal(timelineBusinessDateKey(merged[0]), '2026-03-20')
  assert.equal(merged[0].record.content, '本人原文')
})

test('重复分页不会重复显示，但同一任务的不同事件仍应保留', () => {
  const events = [
    { id: 'create', entity_type: 'relationship_task', entity_id: 'a', event_type: 'task.created' },
    { id: 'done', entity_type: 'relationship_task', entity_id: 'a', event_type: 'task.completed' },
  ]
  const archive = { id: 'record-a', item_type: 'record', local_date: '2026-03-20' }
  const merged = mergeTimelineItems([...events, events[0]], [archive, archive])
  assert.equal(merged.length, 3)
})

test('对方记录只保留接口允许的摘要，按真实类型识别隐私占位', () => {
  const merged = mergeTimelineItems([], [{ id: 'a', item_type: 'partner_record_placeholder', local_date: '2026-03-20', visibility: 'shared_summary', summary: '对方也留下了记录', locked_reason: '原文仅本人可见' }])
  assert.equal(merged[0].tone_label, '仅共享摘要')
  assert.equal(merged[0].record, undefined)
})

test('无效日期不会进入日历，闰年二月正确显示', () => {
  assert.equal(timelineBusinessDateKey('2026-02-31'), '')
  assert.equal(timelineBusinessDateKey('not-a-date'), '')
  assert.equal(buildCalendarDays(2024, 1).filter(day => day.isCurrentMonth).length, 29)
})
test('样例时间轴也必须按关系筛选，双视角样例归到它实际的日期', async () => {
  const { buildDemoTimelineEvents } = await import('./timelineCalendar.js')
  const fixture = { timelineEvents: [{ id: 'e1', pair_id: 'a', title: '甲的记录', timestamp: '2026-03-19T21:10:00' }, { id: 'e2', pair_id: 'b', title: '乙的记录', timestamp: '2026-03-20T10:00:00' }], narrativeAlignment: { pair_id: 'a', event_id: 'alignment-a', checkin_date: '2026-03-21', generated_at: '2026-03-22T01:00:00', shared_story: '分析摘要' } }
  const records = buildDemoTimelineEvents(fixture, 'a')
  assert.deepEqual(records.map(item => item.id), ['e1', 'alignment-a'])
  assert.equal(timelineBusinessDateKey(records[0]), '2026-03-19')
  assert.equal(timelineBusinessDateKey(records[1]), '2026-03-21')
  assert.deepEqual(buildDemoTimelineEvents(fixture, 'missing'), [])
})

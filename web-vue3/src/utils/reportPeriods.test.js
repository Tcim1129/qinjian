import test from 'node:test'
import assert from 'node:assert/strict'
import { buildSampleReports, reportPeriodLabel, selectReportHistory } from './reportPeriods.js'

test('sample periods contain distinct complete snapshots, not daily rows under weekly tabs', () => {
  const base = { health_score: 84, pair_id: 'friend', scope_name: '周宁', dimensions: [{ label: '信任', score: 82 }] }
  for (const type of ['daily', 'weekly', 'monthly']) {
    const rows = buildSampleReports(base, type)
    assert.equal(rows.length, 3)
    assert.ok(rows.every(row => row.report_type === type && row.summary && row.insights.length && row.recommendations.length))
    assert.equal(new Set(rows.map(row => row.report_date)).size, 3)
    assert.notEqual(rows[0].summary, rows[1].summary)
    assert.notDeepEqual(rows[0].dimensions, rows[1].dimensions)
    assert.ok(rows.every(row => row.trend_points.every(point => /^\d{4}-\d{2}-\d{2}$/.test(point.date))))
  }
  assert.equal(base.health_score, 84)
})

test('history filters type and keeps the latest revision for each report day, including zero scores', () => {
  const rows = [
    { id: 'old', report_type: 'daily', report_date: '2026-03-21', created_at: '2026-03-21T10:00:00Z' },
    { id: 'weekly', report_type: 'weekly', report_date: '2026-03-21' },
    { id: 'new', report_type: 'daily', report_date: '2026-03-21', created_at: '2026-03-21T12:00:00Z', health_score: 0 },
    { id: 'yesterday', report_type: 'daily', report_date: '2026-03-20' },
  ]
  assert.deepEqual(selectReportHistory(rows, 'daily').map(row => row.id), ['new', 'yesterday'])
  assert.equal(selectReportHistory(rows, 'daily')[0].health_score, 0)
})

test('period labels use report dates rather than generation timestamps and cross years safely', () => {
  assert.equal(reportPeriodLabel({ report_type: 'daily', report_date: '2026-03-21', created_at: '2026-03-22' }), '2026年3月21日')
  assert.equal(reportPeriodLabel({ report_type: 'weekly', report_date: '2026-01-03' }), '2025年12月27日–2026年1月3日')
  assert.equal(reportPeriodLabel({ report_type: 'monthly', report_date: '2026-03-01' }), '2026年1月30日–2026年3月1日')
  assert.equal(reportPeriodLabel({}), '')
})

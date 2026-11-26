import assert from 'node:assert/strict'
import test from 'node:test'
import { buildHomeRadarAxes, buildHomeTrendView } from './homeAnalytics.js'

test('missing scores stay missing instead of becoming zero in the home trend', () => {
  const missing = buildHomeTrendView({
    reportTrend: { trend: [{ date: '2026-11-25', score: null }, { date: '2026-11-24', score: '' }] },
  })
  assert.equal(missing.points.length, 0)
  const zero = buildHomeTrendView({ reportTrend: { trend: [{ date: '2026-11-25', score: 0 }] } })
  assert.equal(zero.points[0].score, 0)
})

test('a partial assessment does not invent the missing radar dimensions', () => {
  assert.deepEqual(buildHomeRadarAxes({ assessmentTrend: {
    dimension_scores: [{ id: 'connection', score: 80 }, { id: 'trust', score: null }],
  } }), [])
  const scores = { connection: 80, trust: 0, repair: 75, shared_future: 100, vitality: 75 }
  const axes = buildHomeRadarAxes({ assessmentTrend: {
    dimension_scores: Object.entries(scores).map(([id, score]) => ({ id, score })),
  } })
  assert.equal(axes.length, 5)
  assert.equal(axes.find(axis => axis.id === 'trust').value, 0)
})

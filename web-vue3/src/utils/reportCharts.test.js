import test from 'node:test'
import assert from 'node:assert/strict'
import { buildRadarAxes, buildTrendChart, RADAR_CENTER, RADAR_RADIUS } from './reportCharts.js'

test('radar labels stay outside the outer polygon, even for very low scores', () => {
  const low = buildRadarAxes(['表达', '信任', '缓和', '愿景', '活力'].map(label => ({ label, score: 0 })))
  const high = buildRadarAxes(low.map(axis => ({ label: axis.label, score: 100 })))
  low.forEach((axis, index) => {
    assert.equal(axis.labelX, high[index].labelX)
    assert.equal(axis.labelY, high[index].labelY)
    assert.equal(axis.valueLabelY, high[index].valueLabelY)
    assert.ok(Math.hypot(axis.labelX - RADAR_CENTER.x, axis.labelY - RADAR_CENTER.y) > RADAR_RADIUS + 30)
    assert.equal(axis.valueX, RADAR_CENTER.x)
    assert.equal(axis.valueY, RADAR_CENTER.y)
  })
})

test('close trend scores remain exact and readable without exaggerating the scale', () => {
  const chart = buildTrendChart([80, 81, 80, 82].map((score, i) => ({ score, label: `${i + 1}期` })))
  assert.deepEqual(chart.points.map(point => point.score), [80, 81, 80, 82])
  assert.ok(chart.max - chart.min >= 20)
  assert.ok(chart.points[0].y - chart.points[1].y >= 6)
  assert.equal(chart.delta, 2)
  assert.ok(chart.points[0].x >= chart.left + 20, 'first score must leave room beside the y-axis labels')
  assert.ok(chart.ticks.length >= 3)
  assert.ok(chart.ticks.every(tick => tick.score >= 0 && tick.score <= 100))
})

test('flat, boundary and single-value trends have valid coordinates and honest comparisons', () => {
  for (const scores of [[0, 0], [100, 100], [81, 81, 81], [0, 100], [75]]) {
    const chart = buildTrendChart(scores.map((score, i) => ({ label: `${i}`, score })))
    assert.ok(chart.min >= 0 && chart.max <= 100 && chart.max > chart.min)
    assert.ok(chart.points.every(point => Number.isFinite(point.x) && point.y >= chart.top && point.y <= chart.bottom))
    if (scores.length === 1) assert.equal(chart.delta, null)
    if (scores.every(score => score === scores[0])) assert.ok(chart.points.every(point => point.y === chart.points[0].y))
  }
})

test('missing scores are not silently drawn as zero, and dense dates get enough room', () => {
  assert.deepEqual(buildTrendChart([{ label: '昨天', score: null }, { label: '今天', score: '' }]).points, [])
  const chart = buildTrendChart(Array.from({ length: 14 }, (_, i) => ({ label: `9月${i + 1}日`, score: 80 + i / 10 })))
  assert.ok(chart.points.slice(1).every((point, i) => point.x - chart.points[i].x >= 56))
  assert.equal(chart.points[0].shortLabel, '9/1')
  assert.equal(chart.points[13].score, 81.3)
})
